import os
import re
import requests
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel
import json
import io
from pydub import AudioSegment
import threading
import collections # ログ用に追加
from datetime import datetime # ログ用に追加
from flask import Flask, request, jsonify

# --- 環境設定 ---
REWRITER_HOST = os.environ.get("REWRITER_HOST", "rewriter") 
VOICEVOX_HOST = os.environ.get("VOICEVOX_HOST", "voicevox")
STORAGE_HOST = "storage"

app = Flask(__name__)

# --- ログ管理システム ---
# 最新100行のログを保持（古いものから自動削除）
log_buffer = collections.deque(maxlen=100)

def log_message(msg):
    """ターミナルに出力し、同時にメモリ内のバッファに保存する"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg, flush=True)
    log_buffer.append(formatted_msg)

# --- 補助機能 ---
def sanitize_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', '', filename)

# --- 各処理工程 ---

def download_audio(url, output_dir="temp"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    log_message("YouTube情報の解析中...")
    with YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'output')
        safe_title = sanitize_filename(title)

    options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/{safe_title}.%(ext)s',
        'quiet': True, # ログが汚れすぎないように抑制
    }
    
    log_message(f"ダウンロード開始: {safe_title}")
    with YoutubeDL(options) as ydl:
        ydl.download([url])
    return f"{output_dir}/{safe_title}.mp3", safe_title

def transcribe_audio(file_path):
    log_message("Whisperモデル読み込み中...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    log_message("文字起こし実行中（CPU負荷がかかります）...")
    segments, info = model.transcribe(file_path, beam_size=5)
    
    text_result = ""
    for segment in segments:
        # 短いログとして進捗を表示
        log_message(f"[文字起こし] {segment.start:.1f}s >> {segment.text[:20]}...")
        text_result += segment.text + "\n"
    
    return text_result

def rewrite_text(raw_text):
    api_url = f"http://{REWRITER_HOST}:5000/rewrite"
    log_message(f"Gemini APIへ校正依頼を送信中...")
    
    try:
        response = requests.post(api_url, json={"text": raw_text})
        response.raise_for_status()
        rewritten_text = response.json().get("rewritten_text")
        if rewritten_text:
            log_message("校正が完了しました")
            return rewritten_text
        else:
            log_message("警告: 校正テキストが空です")
            return raw_text
    except Exception as e:
        log_message(f"Rewriter通信エラー: {e}")
        return raw_text

def generate_voice(text, output_path, speaker_id=1):
    host = VOICEVOX_HOST
    port = 50021
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    combined_audio = AudioSegment.empty()

    log_message(f"VOICEVOX音声合成開始 (全{len(lines)}行)")

    for i, line in enumerate(lines):
        try:
            # 1行ごとの進捗をログに送る
            if i % 5 == 0 or i == len(lines)-1: # 5行おきに表示してログをスッキリさせる
                log_message(f"音声合成中: {i+1}/{len(lines)}行目")
            
            res_query = requests.post(
                f"http://{host}:{port}/audio_query",
                params={"text": line, "speaker": speaker_id}
            )
            res_query.raise_for_status()
            query = res_query.json()

            res_synthesis = requests.post(
                f"http://{host}:{port}/synthesis",
                params={"speaker": speaker_id},
                headers={'Content-Type': 'application/json'},
                data=json.dumps(query)
            )
            res_synthesis.raise_for_status()
            
            line_audio = AudioSegment.from_wav(io.BytesIO(res_synthesis.content))
            combined_audio += line_audio + AudioSegment.silent(duration=500)
            
        except Exception as e:
            log_message(f"行 {i+1} で合成失敗: {e}")
            continue

    if len(combined_audio) > 0:
        combined_audio.export(output_path, format="wav")
        log_message(f"音声ファイル完成: {len(combined_audio)/1000:.1f}秒")
        return True
    return False

def upload_to_drive(file_path):
    storage_url = "http://storage:5001/upload"
    log_message(f"ドライブ転送中: {os.path.basename(file_path)}")
    try:
        res = requests.post(storage_url, json={"file_path": file_path})
        log_message(f"アップロード完了")
        return res.json()
    except Exception as e:
        log_message(f"アップロード失敗: {e}")

# --- メインロジック ---

def heavy_process(video_url):
    try:
        log_message(f"--- 処理受付: {video_url} ---")
        
        # 1. ダウンロード
        audio_file_path, title = download_audio(video_url)
    
        # 2. 文字起こし
        raw_text = transcribe_audio(audio_file_path)

        # 3. 校正
        rewritten_text = rewrite_text(raw_text)
    
        # ファイル保存
        output_raw_path = f"temp/{title}_raw.txt"
        output_rewritten_path = f"temp/{title}_rewritten.txt"
        with open(output_raw_path, "w", encoding="utf-8") as f: f.write(raw_text)
        with open(output_rewritten_path, "w", encoding="utf-8") as f: f.write(rewritten_text)

        # 4. 音声合成
        output_voice_path = f"temp/{title}_rewritten.wav"
        generate_voice(rewritten_text, output_voice_path) 
    
        # 5. アップロード
        upload_to_drive(output_rewritten_path)
        upload_to_drive(output_voice_path)

        log_message(f"✅ すべての工程が正常に完了しました")
    except Exception as e:
        log_message(f"❌ 致命的エラー: {e}")

# --- APIルート ---

@app.route('/process', methods=['POST'])
def handle_process():
    data = request.json
    video_url = data.get('url')
    if not video_url:
        return jsonify({"status": "error", "message": "URLがありません"}), 400

    thread = threading.Thread(target=heavy_process, args=(video_url,))
    thread.start()

    return jsonify({
        "status": "accepted",
        "message": "処理を開始しました。下のログパネルで進捗を確認してください。"
    })

@app.route('/logs', methods=['GET'])
def get_logs():
    """溜まっているログをJSONで返す"""
    return jsonify({"logs": list(log_buffer)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    