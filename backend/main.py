# DNews backend - fixed main.py
# Minimal FastAPI service that fetches NewsAPI results for several topics,
# caches them, and refreshes every 30 minutes.
# Environment variable required: NEWSAPI_KEY

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, requests, threading, time
from datetime import datetime, timezone

app = FastAPI(title="DNews Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")

# Topic queries tailored to user's request
TOPICS = {
    "policy": "Fed OR Federal Reserve OR ECB OR European Central Bank OR \"State Bank of Vietnam\" OR SBV OR \"interest rate\" OR \"rate hike\" OR \"rate cut\" OR monetary policy",
    "fx": "exchange rate OR USD OR EUR OR currency OR \"tỷ giá\" OR forex",
    "metals": "gold OR silver OR vàng OR bạc OR \"giá vàng\" OR \"giá bạc\" OR platinum",
    "investment": "FDI OR ODA OR \"foreign direct investment\" OR investment OR \"đầu tư nước ngoài\" OR trade OR tariff OR tax",
    "vietnam": "Vietnam OR Vietnam economy OR SBV OR \"Ngân hàng Nhà nước\" OR \"tỷ giá\" OR Cafef OR Vietstock OR VnEconomy OR chính sách"
}

# Simple in-memory cache: { topic_key: [articles...] }, timestamps
cache = {"articles": {}, "last_updated": None}

def fetch_for_topic(topic_key, pageSize=30, language="en"):
    """Fetch articles from NewsAPI for a given topic and language."""
    if not NEWSAPI_KEY:
        return []
    q = TOPICS.get(topic_key, "")
    params = {
        "q": q,
        "language": language,
        "pageSize": pageSize,
        "sortBy": "publishedAt",
        "apiKey": NEWSAPI_KEY,
    }
    try:
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("articles", [])
        else:
            return []
    except Exception:
        return []

def refresh_all():
    """Refresh cache for all topics (both en and vi)."""
    results = {}
    for k in TOPICS.keys():
        en = fetch_for_topic(k, language="en")
        vi = fetch_for_topic(k, language="vi")
        merged = (en or []) + (vi or [])
        # deduplicate by url
        seen = set(); dedup = []
        for it in merged:
            u = it.get("url")
            if not u or u in seen:
                continue
            seen.add(u); dedup.append(it)
        results[k] = dedup
    cache["articles"] = results
    cache["last_updated"] = datetime.now(timezone.utc).isoformat()

def schedule_refresh(interval_minutes=30):
    """Background thread to refresh cache periodically."""
    def loop():
        while True:
            try:
                refresh_all()
            except Exception:
                pass
            time.sleep(interval_minutes * 60)
    t = threading.Thread(target=loop, daemon=True)
    t.start()

@app.on_event("startup")
def on_startup():
    # initial fetch and start background refresher
    try:
        refresh_all()
    except Exception:
        pass
    schedule_refresh(interval_minutes=30)

@app.get("/articles")
def get_articles(topic: str = "policy", limit: int = 30):
    """Return cached articles for a topic. topic: policy, fx, metals, investment, vietnam"""
    if topic not in TOPICS:
        raise HTTPException(status_code=400, detail="Invalid topic")
    data = cache.get("articles", {}).get(topic, [])[:limit]
    return {"topic": topic, "last_updated": cache.get("last_updated"), "count": len(data), "articles": data}

@app.get("/health")
def health():
    return {"status": "ok", "last_updated": cache.get("last_updated")}
