from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

# WorkerコンテナのURL（Dockerネットワーク内のサービス名で指定）
WORKER_URL_BASE = "http://worker:5000"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    # フォーム形式、またはJSON形式の両方に対応できるようにしておく
    video_url = request.form.get('video_url') or request.json.get('url')
    
    if not video_url:
        return jsonify({"status": "error", "message": "URLを入力してください"}), 400
    
    try:
        # workerに処理を依頼
        response = requests.post(f"{WORKER_URL_BASE}/process", json={"url": video_url})
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ここからが追加分：ログの中継役 ---
@app.route('/logs')
def get_worker_logs():
    try:
        # Workerコンテナの /logs APIを叩きに行く
        response = requests.get(f"{WORKER_URL_BASE}/logs", timeout=2)
        return jsonify(response.json())
    except Exception as e:
        # Workerが起動していない場合などのエラーハンドリング
        return jsonify({"logs": [f"Workerに接続できません: {str(e)}"]}), 500

if __name__ == '__main__':
    # 0.0.0.0で外部からのアクセスを許可
    app.run(host='0.0.0.0', port=8000)
    