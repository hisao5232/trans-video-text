// ページ読み込み完了時にログ更新を開始
document.addEventListener('DOMContentLoaded', () => {
    // 2秒ごとにログを更新する
    setInterval(updateLogs, 2000);
});

async function submitUrl() {
    const urlInput = document.getElementById('videoUrl');
    const resultMsg = document.getElementById('result-msg');
    const button = document.getElementById('submitBtn');

    if (!urlInput.value) {
        showMessage("URLを入力してください", "error");
        return;
    }

    // UIを「処理中」の状態にする
    button.disabled = true;
    showMessage("リクエスト送信中...", "");

    try {
        const response = await fetch('/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `video_url=${encodeURIComponent(urlInput.value)}`
        });

        const data = await response.json();

        if (response.ok) {
            showMessage(data.message, "success");
            urlInput.value = ''; // 入力欄をクリア
        } else {
            showMessage("エラー: " + data.message, "error");
            button.disabled = false;
        }
    } catch (e) {
        showMessage("通信エラーが発生しました", "error");
        button.disabled = false;
    }
}

async function updateLogs() {
    const logPanel = document.getElementById('log-panel');
    try {
        const response = await fetch('/logs');
        if (!response.ok) return;
        
        const data = await response.json();
        
        // ログを更新（改行コードで結合）
        if (data.logs && data.logs.length > 0) {
            logPanel.innerText = data.logs.join('\n');
            // 常に一番下まで自動スクロール
            logPanel.scrollTop = logPanel.scrollHeight;
        }
    } catch (e) {
        console.error("ログ取得エラー:", e);
    }
}

function showMessage(text, className) {
    const msgDiv = document.getElementById('result-msg');
    msgDiv.innerText = text;
    msgDiv.className = className;
}
