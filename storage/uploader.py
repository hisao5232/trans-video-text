import os
from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = 'token.json'  # 先ほどアップロードしたファイル
PARENT_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")

def get_drive_service():
    # token.json を使ってあなた本人として認証
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(f"{TOKEN_FILE} が見つかりません。")
    
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build('drive', 'v3', credentials=creds)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        data = request.json
        file_path = data.get('file_path')
        service = get_drive_service()

        print(f"DEBUG: OAuth2 Uploading {file_path}", flush=True)

        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [PARENT_FOLDER_ID]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"DEBUG: Success! File ID: {file.get('id')}", flush=True)
        return jsonify({"status": "success", "file_id": file.get('id')})

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}", flush=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
    