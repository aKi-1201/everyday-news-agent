"""
用 LINE Messaging API 的 push message 推播訊息給指定使用者。
文件: https://developers.line.biz/en/reference/messaging-api/#send-push-message
"""
import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_TEXT_LIMIT = 4900  # LINE 文字訊息上限為 5000 字元，留一點緩衝


def push_line_text(channel_access_token: str, user_id: str, text: str) -> None:
    if not channel_access_token or not user_id:
        raise ValueError("尚未設定 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID")

    if len(text) > LINE_TEXT_LIMIT:
        text = text[:LINE_TEXT_LIMIT - 20] + "\n...(內容過長已截斷)"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}],
    }
    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"LINE 推播失敗 ({resp.status_code}): {resp.text}")
