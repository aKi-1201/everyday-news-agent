"""
用 Gemini API 把蒐集到的原始資料整理成一則早報文字。
刻意用最原始的 REST 呼叫方式（requests 直打 API），而不是 google-genai SDK，
理由：SDK 套件名稱/介面這幾年變動頻繁，REST endpoint 相對穩定，個人專案維護成本較低。
"""
import requests

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SYSTEM_PROMPT = """你是一位財經新聞編輯，請根據使用者提供的「原始資料」整理一份繁體中文的早報，規則：
1. 只能使用使用者提供的資料，禁止自行補充你記憶中的數字、新聞或網址，不確定的地方寧可省略也不要編造。
2. 輸出格式依序為：📈 美股隔夜、📰 新聞焦點、💰 Fed / 經濟數據行事曆，三段之間用空行分隔。
3. 新聞焦點段落挑 3-5 則最重要的整合，依照重要程度排列，每則新聞下方緊接著附上原始資料中提供的「連結」網址原文（一字不改，不要用 Markdown 語法包裝），若某則新聞的原始資料沒有附連結就不要附。
4. 每段控制在精簡扼要即可。
5. 不要加入客套的開場白或結語，直接輸出早報內容，適合放進 LINE 訊息中閱讀。
6. 使用台灣人習慣的用語與繁體中文。"""


def summarize_with_gemini(api_key: str, model: str, raw_data: str) -> str:
    if not api_key:
        raise ValueError("尚未設定 GEMINI_API_KEY")

    url = GEMINI_ENDPOINT.format(model=model)
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": raw_data}]}],
        "generationConfig": {"temperature": 0.3},
    }
    resp = requests.post(
        url,
        params={"key": api_key},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Gemini 回應格式異常，無法解析: {data}") from e
