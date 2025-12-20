from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# workerコンテナのURL（Dockerネットワーク内なのでサービス名で指定）
WORKER_URL = "http://worker:5000/process"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    video_url = request.form.get('video_url')
    if not video_url:
        return jsonify({"status": "error", "message": "URLを入力してください"}), 400
    
    try:
        # workerに処理を依頼
        response = requests.post(WORKER_URL, json={"url": video_url})
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
    