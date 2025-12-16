import os
import re  # ファイル名洗浄用
import requests
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel

# --- 環境変数からホスト名を取得 (docker-compose.ymlで設定したサービス名) ---
REWRITER_HOST = os.environ.get("REWRITER_HOST", "rewriter")
# --- 環境変数からホスト名を取得 ---
REWRITER_HOST = os.environ.get("REWRITER_HOST", "rewriter") 
# VOICEVOX連携用に追加
VOICEVOX_HOST = os.environ.get("VOICEVOX_HOST", "voicevox")

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

if __name__ == "__main__":
    video_url = "https://youtu.be/q0p5rg_6OKg"
    
    print("--- ダウンロード開始 ---")
    audio_file_path, title = download_audio(video_url)
    
    print(f"--- 文字起こし開始: {title} ---")
    raw_text = transcribe_audio(audio_file_path)

# 2. Geminiによる校正（NEW）
    rewritten_text = rewrite_text(raw_text)
    
# 3. テキストファイルを保存
    output_raw_path = f"temp/{title}_raw.txt" # 生テキスト
    output_rewritten_path = f"temp/{title}_rewritten.txt" # 校正済みテキスト
    
    with open(output_raw_path, "w", encoding="utf-8") as f:
        f.write(raw_text)
        
    with open(output_rewritten_path, "w", encoding="utf-8") as f:
        f.write(rewritten_text)
        
    print(f"--- 完了 ---")
    print(f"生テキスト保存先: {output_raw_path}")
    print(f"校正済みテキスト保存先: {output_rewritten_path}")
