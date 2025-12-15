FROM python:3.10-slim

# ffmpegのインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ライブラリのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# コンテナが勝手に終了しないようにする（後でAPI化するため）
CMD ["tail", "-f", "/dev/null"]
