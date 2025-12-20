FROM python:3.10-slim

WORKDIR /app

# 必要なパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY uploader.py .
# JSON鍵は docker-compose.yml の volumes でマウントするので、Dockerfileでのコピーは不要です（安全のため）

# Flaskサーバーを起動
CMD ["python", "uploader.py"]
