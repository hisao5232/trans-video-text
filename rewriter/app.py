from flask import Flask, request, jsonify
from google import genai
import os

app = Flask(__name__)

# 環境変数からAPIキーを取得
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# モデルとプロンプトの定義
MODEL_NAME = "gemini-2.5-flash"

def rewrite_text_with_gemini(raw_text):
    """Gemini APIを使用して文章を自然に校正する"""
    
    # ここがコアとなるプロンプトです
    system_instruction = (
        "あなたはプロの校正者です。提供された日本語の文字起こしテキストを、"
        "誤字脱字、話し言葉特有の不自然さ（例: 誤った漢字、リズムの不整合）を修正し、"
        "意味を変えずに読みやすい自然な文章に書き換えてください。ただし、句読点は適切に残してください。"
    )
    
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=raw_text,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_instruction
        )
    )
    return response.text

@app.route('/rewrite', methods=['POST'])
def rewrite():
    data = request.json
    raw_text = data.get('text')
    
    if not raw_text:
        return jsonify({"error": "No text provided"}), 400

    try:
        rewritten_text = rewrite_text_with_gemini(raw_text)
        return jsonify({"rewritten_text": rewritten_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 開発環境用の設定（本番ではGunicornなどを使用推奨）
    app.run(host='0.0.0.0', port=5000)
    