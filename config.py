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

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")  # 留空則自動略過 Fed 數據段落

# ============ 台灣新聞 RSS 來源 ============
# 來源皆為官方公開 RSS，個人非商業用途免費使用，請勿移除新聞出處。
# 自由時報 RSS 清單: https://service.ltn.com.tw/RSS
# 中央社 RSS 清單:   https://www.cna.com.tw/about/rss.aspx
RSS_FEEDS = {
    "自由時報-即時": "https://news.ltn.com.tw/rss/all.xml",  # 焦點 RSS (focus.xml) 已關閉，改回全站即時
    "中央社-政治": "https://feeds.feedburner.com/rsscna/politics",
    "中央社-國際": "https://feeds.feedburner.com/rsscna/intworld",
    "中央社-科技": "https://feeds.feedburner.com/rsscna/technology",
    "中央社-產經證券": "https://feeds.feedburner.com/rsscna/finance",
    "經濟日報": "https://money.udn.com/rssfeed/news",
    "關鍵評論網": "https://www.thenewslens.com/feed/feedly",
    "TechNews 科技新報": "https://technews.tw/feed/",
}
HEADLINES_PER_SOURCE = 10  # 每個新聞來源取幾則標題餵給 LLM（8 來源 x 10 則，讓編輯室摘要有足夠素材）

# ============ 美股觀察指數（同時設定 Stooq 與 Yahoo 代碼，其中一個抓不到就自動改用另一個） ============
US_INDICES = {
    "S&P 500": {"stooq": "^spx", "yahoo": "^GSPC"},
    "Nasdaq": {"stooq": "^ndq", "yahoo": "^IXIC"},
    "道瓊工業指數": {"stooq": "^dji", "yahoo": "^DJI"},
    "費城半導體指數": {"stooq": "^sox", "yahoo": "^SOX"},  # Yahoo代碼已確認；Stooq代碼若失效會自動改用Yahoo
}

# ============ 美股休市判斷 ============
# 已改用 pandas_market_calendars 套件自動判斷（見 sources.py 的 is_us_market_likely_closed），
# 內建 NYSE 官方假日規則且會自動處理浮動假日，不需要在這裡手動維護清單了。
# 完整 release 列表: https://fred.stlouisfed.org/releases
# 序列代碼可在該序列頁面網址找到，例如 https://fred.stlouisfed.org/series/CPIAUCSL
FRED_RELEASES = {
    "CPI 消費者物價指數": {"release_id": 10, "series_id": "CPIAUCSL"},
    "非農就業報告 (Employment Situation)": {"release_id": 50, "series_id": "PAYEMS"},
}
