"""
資料蒐集模組。
設計原則：每個 fetch 函式都「只回傳事實資料的文字區塊」，不做任何摘要或判斷，
確保後面餵給 Gemini 的是可查證的原始資訊，避免 LLM 憑空生成數字。
任何一個來源抓取失敗都不應讓整支程式掛掉，因此逐一包 try/except。
"""
import logging
from datetime import datetime, timezone

import feedparser
import requests

log = logging.getLogger("daily-news-agent.sources")

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


def _trend_emoji(change: float) -> str:
    """依漲跌方向回傳對應符號，交給程式碼決定，避免 LLM 判斷錯誤。"""
    if change > 0:
        return "📈"
    if change < 0:
        return "📉"
    return "➡️"


def _parse_stooq(symbol: str):
    """從 Stooq 抓 CSV，回傳 (今日收盤, 前一日收盤, 日期字串)。"""
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    resp = requests.get(url, timeout=TIMEOUT, headers=UA_HEADERS)
    resp.raise_for_status()
    rows = [r.split(",") for r in resp.text.strip().splitlines() if r][1:]  # 去表頭
    if len(rows) < 2:
        # Stooq 對雲端主機（如 Oracle/AWS）的 IP 有時會回傳空資料擋爬蟲，改試 Yahoo。
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
    """依序嘗試 Stooq -> Yahoo，任一來源成功就回傳（含漲跌符號），兩者都失敗才回報抓取失敗。"""
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
            emoji = _trend_emoji(change)
            return (
                f"{emoji} {name}：{close_today:,.2f}"
                f"（{change:+.2f}，{pct:+.2f}%）[{date_today}，來源:{source_name}]"
            )
        except Exception as e:
            errors.append(f"{source_name}失敗({e})")
    return f"{name}：抓取失敗（{'；'.join(errors) if errors else '未設定任何來源代碼'}）"


def fetch_us_market_summary(indices: dict) -> str:
    """組合所有美股指數的摘要文字。indices 格式見 config.py 的 US_INDICES。"""
    return "\n".join(_fetch_index(name, symbols) for name, symbols in indices.items())


def fetch_fred_todays_releases(api_key: str, releases: dict) -> str:
    """
    檢查「今天」是否有指定的經濟數據公布，若有才抓取最新數值與前一期比較。
    回傳空字串代表今天沒有任何一項數據公布（或未設定金鑰），呼叫端應直接省略這個段落，
    不要在推播中出現空段落。
    releases 格式: {"顯示名稱": {"release_id": int, "series_id": str}}
    """
    if not api_key:
        log.warning("未設定 FRED_API_KEY，略過 Fed 經濟數據查詢")
        return ""

    today = datetime.now(timezone.utc).date().isoformat()
    blocks = []
    for name, meta in releases.items():
        release_id = meta["release_id"]
        series_id = meta["series_id"]
        try:
            date_url = (
                "https://api.stlouisfed.org/fred/release/dates"
                f"?release_id={release_id}&realtime_start={today}&realtime_end={today}"
                f"&api_key={api_key}&file_type=json&include_release_dates_with_no_data=true"
            )
            resp = requests.get(date_url, timeout=TIMEOUT)
            resp.raise_for_status()
            dates = [d["date"] for d in resp.json().get("release_dates", [])]
            if today not in dates:
                continue  # 今天沒有這項數據公布，跳過，不算錯誤

            obs_url = (
                "https://api.stlouisfed.org/fred/series/observations"
                f"?series_id={series_id}&sort_order=desc&limit=2"
                f"&api_key={api_key}&file_type=json"
            )
            obs_resp = requests.get(obs_url, timeout=TIMEOUT)
            obs_resp.raise_for_status()
            observations = obs_resp.json().get("observations", [])
            valid_obs = [o for o in observations if o.get("value") not in (None, ".")]
            if len(valid_obs) < 2:
                blocks.append(f"- {name}：今日公布，但可比對的歷史資料筆數不足")
                continue

            latest, prev = valid_obs[0], valid_obs[1]
            latest_val, prev_val = float(latest["value"]), float(prev["value"])
            change = latest_val - prev_val
            pct = change / prev_val * 100 if prev_val else 0
            emoji = _trend_emoji(change)
            blocks.append(
                f"- {name}（資料期間 {latest['date']}）{emoji}：{latest_val:,.2f}"
                f"（較上期 {change:+.2f}，{pct:+.2f}%）"
            )
        except Exception as e:
            blocks.append(f"- {name}：查詢失敗（{e}）")

    return "\n".join(blocks)
