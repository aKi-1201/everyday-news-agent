"""
資料蒐集模組。
設計原則：每個 fetch 函式都「只回傳事實資料的文字區塊」，不做任何摘要或判斷，
確保後面餵給 Gemini 的是可查證的原始資訊，避免 LLM 憑空生成數字。
任何一個來源抓取失敗都不應讓整支程式掛掉，因此逐一包 try/except。
"""
import feedparser
import requests
from datetime import datetime, timedelta, timezone

TIMEOUT = 10
UA_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyNewsBot/1.0)"}


def fetch_rss_headlines(feeds: dict, limit_per_source: int) -> str:
    """抓取多個 RSS 來源的最新標題與連結。"""
    blocks = []
    for name, url in feeds.items():
        try:
            resp = requests.get(url, timeout=TIMEOUT, headers=UA_HEADERS)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            lines = []
            for entry in feed.entries[:limit_per_source]:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                lines.append(f"- {title}\n  連結: {link}" if link else f"- {title}")
            if lines:
                blocks.append(f"【{name}】\n" + "\n".join(lines))
            else:
                blocks.append(f"【{name}】（本次未取得任何項目）")
        except Exception as e:
            blocks.append(f"【{name}】抓取失敗：{e}")
    return "\n\n".join(blocks)


def _parse_stooq(symbol: str):
    """從 Stooq 抓 CSV，回傳 (今日收盤, 前一日收盤, 日期字串)。"""
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    resp = requests.get(url, timeout=TIMEOUT, headers=UA_HEADERS)
    resp.raise_for_status()
    rows = [r.split(",") for r in resp.text.strip().splitlines() if r][1:]  # 去表頭
    if len(rows) < 2:
        # Stooq 對雲端主機（如 Oracle/AWS）的 IP 有時會回傳空資料或錯誤頁面擋爬蟲，
        # 這裡直接拋例外，讓上層改試 Yahoo Finance。
        raise ValueError("回傳資料筆數不足，可能被判定為機器人流量而擋下")
    date_today, close_today = rows[-1][0], float(rows[-1][4])
    close_prev = float(rows[-2][4])
    return close_today, close_prev, date_today


def _parse_yahoo(symbol: str):
    """從 Yahoo Finance 公開 chart API 抓資料，作為 Stooq 的備援來源。"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    resp = requests.get(
        url, params={"range": "5d", "interval": "1d"}, timeout=TIMEOUT, headers=UA_HEADERS
    )
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    timestamps = result["timestamp"]
    valid = [(t, c) for t, c in zip(timestamps, closes) if c is not None]
    if len(valid) < 2:
        raise ValueError("回傳資料筆數不足")
    (_, close_prev), (t_today, close_today) = valid[-2], valid[-1]
    date_today = datetime.fromtimestamp(t_today, tz=timezone.utc).strftime("%Y-%m-%d")
    return close_today, close_prev, date_today


def _fetch_index(name: str, symbols: dict) -> str:
    """依序嘗試 Stooq -> Yahoo，任一來源成功就回傳，兩者都失敗才回報抓取失敗。"""
    attempts = [("Stooq", _parse_stooq, symbols.get("stooq")),
                ("Yahoo", _parse_yahoo, symbols.get("yahoo"))]
    errors = []
    for source_name, parse_fn, symbol in attempts:
        if not symbol:
            continue
        try:
            close_today, close_prev, date_today = parse_fn(symbol)
            change = close_today - close_prev
            pct = change / close_prev * 100 if close_prev else 0
            return f"{name}：{close_today:,.2f}（{change:+.2f}，{pct:+.2f}%）[{date_today}，來源:{source_name}]"
        except Exception as e:
            errors.append(f"{source_name}失敗({e})")
    return f"{name}：抓取失敗（{'；'.join(errors) if errors else '未設定任何來源代碼'}）"


def fetch_us_market_summary(indices: dict) -> str:
    """組合所有美股指數的摘要文字。indices 格式見 config.py 的 US_INDICES。"""
    return "\n".join(_fetch_index(name, symbols) for name, symbols in indices.items())


def fetch_fred_upcoming_releases(api_key: str, releases: dict, days_ahead: int) -> str:
    """
    查詢 FRED 指定幾個經濟數據，未來 N 天內是否有公布排程。
    需要免費申請 FRED API Key: https://fred.stlouisfed.org/docs/api/api_key.html
    """
    if not api_key:
        return "（未設定 FRED_API_KEY，略過經濟數據行事曆）"

    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=days_ahead)
    lines = []
    for name, release_id in releases.items():
        url = (
            "https://api.stlouisfed.org/fred/release/dates"
            f"?release_id={release_id}"
            f"&realtime_start={today.isoformat()}&realtime_end={end.isoformat()}"
            f"&api_key={api_key}&file_type=json&include_release_dates_with_no_data=true"
        )
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            dates = [d["date"] for d in resp.json().get("release_dates", [])]
            if dates:
                lines.append(f"- {name}：{', '.join(dates)}")
        except Exception as e:
            lines.append(f"- {name}：查詢失敗（{e}）")
    return "\n".join(lines) if lines else "（未來期間內查無排定公布的數據）"


def fetch_fomc_reminder(meeting_dates: list) -> str:
    """單純把手動維護的 FOMC 會議日期列出來，不做日期比對邏輯（保持簡單好維護）。"""
    if not meeting_dates:
        return "（尚未設定 FOMC 會議日期，請至 config.py 依官方行事曆填入）"
    return "\n".join(f"- {d}" for d in meeting_dates)
