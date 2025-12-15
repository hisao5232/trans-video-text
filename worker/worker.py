import os
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel

def download_audio(url, output_dir="temp"):
    """YouTubeから音声のみをダウンロードする"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/%(id)s.%(ext)s',
    }
    
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"{output_dir}/{info['id']}.mp3"

def transcribe_audio(file_path):
    """音声を文字起こしする"""
    # CPUで動作させる設定 (GPUがある場合は 'cuda' に変更)
    model = WhisperModel("base", device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(file_path, beam_size=5)
    
    text_result = ""
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        text_result += segment.text + "\n"
    
    return text_result

# 実行テスト
if __name__ == "__main__":
    video_url = "https://youtu.be/q0p5rg_6OKg"
    
    print("--- ダウンロード開始 ---")
    audio_file = download_audio(video_url)
    
    print("--- 文字起こし開始 ---")
    result_text = transcribe_audio(audio_file)
    
    # テキストファイルに保存
    with open("temp/output.txt", "w", encoding="utf-8") as f:
        f.write(result_text)
    
    print("--- 完了 ---")
