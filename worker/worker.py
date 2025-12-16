import os
import re  # ファイル名洗浄用
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel

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

if __name__ == "__main__":
    video_url = "https://youtu.be/q0p5rg_6OKg"
    
    print("--- ダウンロード開始 ---")
    audio_file_path, title = download_audio(video_url)
    
    print(f"--- 文字起こし開始: {title} ---")
    result_text = transcribe_audio(audio_file_path)
    
    # タイトルをファイル名にして保存
    output_text_path = f"temp/{title}.txt"
    with open(output_text_path, "w", encoding="utf-8") as f:
        f.write(result_text)
    
    print(f"--- 完了: {output_text_path} ---")