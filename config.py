"""
設定檔：所有金鑰一律從環境變數讀取（實際值放在 .env，不要 commit 進版控）。
新聞來源、觀察指數等「內容設定」則直接寫在這裡，方便日後自行增減。
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # 自動讀取專案資料夾下的 .env，找不到檔案也不會報錯
except ImportError:
    pass  # 沒裝 python-dotenv 也沒關係，退回用系統環境變數

# ============ API 金鑰 / Token（從環境變數讀取） ============
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")  # 你自己的 LINE userId（推播目標）

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")  # 留空則自動略過 Fed 數據行事曆

# ============ 台灣新聞 RSS 來源 ============
# 來源皆為官方公開 RSS，個人非商業用途免費使用，請勿移除新聞出處。
# 自由時報 RSS 清單: https://service.ltn.com.tw/RSS
# 中央社 RSS 清單:   https://www.cna.com.tw/about/rss.aspx
RSS_FEEDS = {
    "自由時報-即時": "https://news.ltn.com.tw/rss/all.xml",
    "自由時報-財經": "https://news.ltn.com.tw/rss/business.xml",
    "中央社-科技": "https://feeds.feedburner.com/rsscna/technology",
    "中央社-產經證券": "https://feeds.feedburner.com/rsscna/finance",
    "經濟日報": "https://money.udn.com/rssfeed/news"
}
HEADLINES_PER_SOURCE = 6  # 每個新聞來源取幾則標題餵給 LLM

# ============ 美股觀察指數（同時設定 Stooq 與 Yahoo 代碼，其中一個抓不到就自動改用另一個） ============
US_INDICES = {
    "S&P 500": {"stooq": "^spx", "yahoo": "^GSPC"},
    "Nasdaq": {"stooq": "^ndq", "yahoo": "^IXIC"},
    "道瓊工業指數": {"stooq": "^dji", "yahoo": "^DJI"},
    "VIX 恐慌指數": {"stooq": "^vix", "yahoo": "^VIX"},
}

# ============ Fed / 美國經濟數據行事曆（FRED release_id） ============
# 完整 release 列表可查: https://fred.stlouisfed.org/releases
FRED_RELEASES = {
    "CPI 消費者物價指數": 10,
    "非農就業報告 (Employment Situation)": 50,
}
FRED_LOOKAHEAD_DAYS = 10  # 查詢未來幾天內的公布日期

# ============ FOMC 會議日期 ============
# FRED 沒有專門的 FOMC 會議 API，這裡採「手動維護」最省事。
# 每年年初到 https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm 覆蓋更新即可。
FOMC_MEETING_DATES = [
    # "YYYY-MM-DD ~ YYYY-MM-DD",  範例，請自行填入當年度官方公布的日期
    
]
