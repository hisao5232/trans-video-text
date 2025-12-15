# YouTube Transcriber & Voice Synthesis

YouTubeのURLを入力すると、音声をダウンロードして文字起こしを行い、さらにVOICEVOXで音声合成を行うプロジェクトです。

## システム構成
- **Worker**: Python (yt-dlp, faster-whisper)
- **Voice Engine**: VOICEVOX Engine (CPU)
- **Infrastructure**: Docker Compose

## 使い方
1. `docker compose up -d` で起動
2. `docker compose exec worker python worker.py` で実行
