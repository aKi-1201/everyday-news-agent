#!/usr/bin/env python3
"""
每日新聞早報 Agent - 主程式
流程：抓取原始資料 -> 丟給 Gemini 整理 -> 用 LINE 推播給自己
用法：python3 main.py
建議透過 cron 每天早上排程執行（見 README.md）。
"""
import logging
import sys
from datetime import datetime

import config
from notifier import push_line_text
from sources import (
    fetch_fomc_reminder,
    fetch_fred_upcoming_releases,
    fetch_rss_headlines,
    fetch_us_market_summary,
)
from summarizer import summarize_with_gemini

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("daily-news-agent")


def collect_raw_data() -> str:
    log.info("抓取美股指數...")
    us_market = fetch_us_market_summary(config.US_INDICES)

    log.info("抓取台灣新聞 RSS...")
    tw_news = fetch_rss_headlines(config.RSS_FEEDS, config.HEADLINES_PER_SOURCE)

    log.info("查詢 FRED 經濟數據行事曆...")
    fred_calendar = fetch_fred_upcoming_releases(
        config.FRED_API_KEY, config.FRED_RELEASES, config.FRED_LOOKAHEAD_DAYS
    )

    fomc = fetch_fomc_reminder(config.FOMC_MEETING_DATES)

    today_str = datetime.now().strftime("%Y-%m-%d")
    return f"""[資料日期] {today_str}

[美股主要指數]
{us_market}

[台灣新聞標題]
{tw_news}

[未來 {config.FRED_LOOKAHEAD_DAYS} 天內經濟數據公布排程]
{fred_calendar}

[FOMC 會議日期]
{fomc}
"""


def main() -> int:
    try:
        raw_data = collect_raw_data()
        log.info("原始資料蒐集完成，長度 %d 字元", len(raw_data))
    except Exception:
        log.exception("資料蒐集階段發生未預期錯誤")
        return 1

    try:
        log.info("呼叫 Gemini 進行摘要整理...")
        summary = summarize_with_gemini(config.GEMINI_API_KEY, config.GEMINI_MODEL, raw_data)
    except Exception:
        log.exception("Gemini 摘要失敗")
        return 1

    try:
        log.info("推播至 LINE...")
        push_line_text(config.LINE_CHANNEL_ACCESS_TOKEN, config.LINE_USER_ID, summary)
        log.info("推播完成")
    except Exception:
        log.exception("LINE 推播失敗")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
