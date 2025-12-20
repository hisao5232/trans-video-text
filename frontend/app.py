from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import requests
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key") # セッション暗号化用

# WorkerコンテナのURL（Dockerネットワーク内のサービス名で指定）
WORKER_URL_BASE = "http://worker:5000"

# --- ログイン管理の設定 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login" # 未ログイン時に飛ばす先

# 簡易的なユーザーモデル
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# 今回は自分一人だけなので、特定のユーザー名とパスワードを想定
USER_ID = "hisao5232"
USER_PASS = os.environ.get("APP_PASSWORD", "admin123") # 初期パスワード

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id == USER_ID else None

# --- ルート設定 ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USER_ID and password == USER_PASS:
            login_user(User(username))
            return redirect(url_for('index'))
        flash('ユーザー名またはパスワードが違います')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required # ログイン必須にする
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
@login_required # ログイン必須にする
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
@login_required # ログもログインしないと見れないようにする
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
