import os
import re  # ファイル名洗浄用
import requests
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel
import json
import io
from pydub import AudioSegment

# --- 環境設定 ---
REWRITER_HOST = os.environ.get("REWRITER_HOST", "rewriter") 
VOICEVOX_HOST = os.environ.get("VOICEVOX_HOST", "voicevox")
STORAGE_HOST = "storage"

def sanitize_filename(filename):
    """ファイル名に使えない文字を削除・置換する"""
    return re.sub(r'[\\/:*?"<>|]', '', filename)

def download_audio(url, output_dir="temp"):
    """YouTubeから音声のみをダウンロードし、タイトルを返す"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # タイトル取得のために一度情報を抽出
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
        # ファイル名をタイトルにする設定
        'outtmpl': f'{output_dir}/{safe_title}.%(ext)s',
    }
    
    with YoutubeDL(options) as ydl:
        ydl.download([url])
        return f"{output_dir}/{safe_title}.mp3", safe_title

def transcribe_audio(file_path):
    """音声を文字起こしする"""
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(file_path, beam_size=5)
    
    text_result = ""
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        text_result += segment.text + "\n"
    
    return text_result

def rewrite_text(raw_text):
    """RewriterコンテナのAPIを呼び出し、Geminiで校正する"""
    api_url = f"http://{REWRITER_HOST}:5000/rewrite"
    
    print(f"--- Rewriter API ({api_url}) へ校正リクエストを送信 ---")
    
    try:
        response = requests.post(api_url, json={"text": raw_text})
        response.raise_for_status() # HTTPエラーが発生した場合に例外を投げる
        
        rewritten_text = response.json().get("rewritten_text")
        if rewritten_text:
            return rewritten_text
        else:
            print("警告: Rewriterから有効な校正済みテキストが返されませんでした。生テキストを使用します。")
            return raw_text
            
    except requests.exceptions.RequestException as e:
        print(f"エラー: Rewriterコンテナとの通信に失敗しました。生テキストを使用します。エラー: {e}")
        return raw_text

def generate_voice(text, output_path, speaker_id=1):
    host = VOICEVOX_HOST
    port = 50021
    
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # AudioSegmentの空オブジェクトを作成
    combined_audio = AudioSegment.empty()

    print(f"--- VOICEVOX: 全{len(lines)}行の合成を開始 ---")

    for i, line in enumerate(lines):
        try:
            print(f"[{i+1}/{len(lines)}] 合成中: {line[:20]}...")
            
            # 1. クエリ作成
            res_query = requests.post(
                f"http://{host}:{port}/audio_query",
                params={"text": line, "speaker": speaker_id}
            )
            res_query.raise_for_status()
            query = res_query.json()

            # 2. 音声合成
            res_synthesis = requests.post(
                f"http://{host}:{port}/synthesis",
                params={"speaker": speaker_id},
                headers={'Content-Type': 'application/json'},
                data=json.dumps(query)
            )
            res_synthesis.raise_for_status()
            
            # 3. バイナリをAudioSegmentオブジェクトに変換して結合
            # BytesIOを使ってメモリ上のバイナリをファイルのように扱う
            line_audio = AudioSegment.from_wav(io.BytesIO(res_synthesis.content))
            
            # 1行ごとに0.5秒（500ミリ秒）の無音を挟むと自然になります
            combined_audio += line_audio + AudioSegment.silent(duration=500)
            
        except Exception as e:
            print(f"警告: {i+1}行目の合成でエラーが発生しました。: {e}")
            continue

    if len(combined_audio) > 0:
        # 最後に一括で書き出し（ヘッダも自動修復される）
        combined_audio.export(output_path, format="wav")
        print(f"音声ファイル保存完了（長さ: {len(combined_audio)/1000:.1f}秒）: {output_path}")
        return True
    else:
        print("エラー: 音声データが生成されませんでした。")
        return False

def upload_to_drive(file_path):
    storage_url = "http://storage:5001/upload"
    try:
        res = requests.post(storage_url, json={"file_path": file_path})
        return res.json()
    except Exception as e:
        print(f"アップロード失敗: {e}")

if __name__ == "__main__":
    # テスト用のURL（適宜変更してください）
    video_url = "https://youtu.be/oruiPIfcTmY"
    
    print("--- ダウンロード開始 ---")
    audio_file_path, title = download_audio(video_url)
    
    print(f"--- 文字起こし開始: {title} ---")
    raw_text = transcribe_audio(audio_file_path)

    print("3. Geminiで校正中...")
    rewritten_text = rewrite_text(raw_text)
    
    # 3. テキストファイルを保存
    output_raw_path = f"temp/{title}_raw.txt" # 生テキスト
    output_rewritten_path = f"temp/{title}_rewritten.txt" # 校正済みテキスト
    
    with open(output_raw_path, "w", encoding="utf-8") as f:
        f.write(raw_text)
        
    with open(output_rewritten_path, "w", encoding="utf-8") as f:
        f.write(rewritten_text)
        
    print(f"生テキスト保存先: {output_raw_path}")
    print(f"校正済みテキスト保存先: {output_rewritten_path}")

    print("4. VOICEVOXで音声合成中...")
    output_voice_path = f"temp/{title}_rewritten.wav"
    
    # 校正済みのテキストを使って音声合成を実行
    generate_voice(rewritten_text, output_voice_path, speaker_id=1) 
    
    print("5. Google Driveへアップロード中...")
    upload_to_drive(output_rewritten_path) # テキスト
    upload_to_drive(output_voice_path)     # 音声

    print(f"--- 全処理完了 ---")
    