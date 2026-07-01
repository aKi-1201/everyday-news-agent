"""
用 LINE Messaging API 的 push message 推播訊息給指定使用者。
文件: https://developers.line.biz/en/reference/messaging-api/#send-push-message
"""
import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_TEXT_LIMIT = 4900  # LINE 文字訊息上限為 5000 字元，留一點緩衝
LINE_MAX_MESSAGES_PER_PUSH = 5  # LINE push API 一次最多可帶 5 則 messages


def _truncate(text: str) -> str:
    if len(text) > LINE_TEXT_LIMIT:
        return text[: LINE_TEXT_LIMIT - 20] + "\n...(內容過長已截斷)"
    return text


def push_line_text(channel_access_token: str, user_id: str, text: str) -> None:
    """推播單一則文字訊息。"""
    push_line_texts(channel_access_token, user_id, [text])


def push_line_texts(channel_access_token: str, user_id: str, texts: list[str]) -> None:
    """
    一次推播多則文字訊息（會顯示成多個分開的訊息泡泡）。
    LINE push API 一次最多接受 5 則 messages，超過的部分會被截掉並記錄警告。
    """
    if not channel_access_token or not user_id:
        raise ValueError("尚未設定 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID")
    if not texts:
        raise ValueError("texts 不能為空")

    if len(texts) > LINE_MAX_MESSAGES_PER_PUSH:
        texts = texts[:LINE_MAX_MESSAGES_PER_PUSH]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": _truncate(t)} for t in texts],
    }
    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"LINE 推播失敗 ({resp.status_code}): {resp.text}")
