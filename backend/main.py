\
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

    # Topics mapped to keyword queries
    TOPICS = {
        "policy": "Fed OR Federal Reserve OR ECB OR European Central Bank OR \"State Bank of Vietnam\" OR SBV OR \"interest rate\" OR \"rate hike\" OR \"rate cut\"",
        "fx": "exchange rate OR USD OR EUR OR currency OR \"tỷ giá\"",
        "metals": "gold OR silver OR vàng OR bạc OR \"giá vàng\" OR \"giá bạc\"",
        "investment": "FDI OR ODA OR \"foreign direct investment\" OR investment OR \"đầu tư nước ngoài\"",
        "vietnam": "Vietnam OR Vietnam economy OR SBV OR \"Ngân hàng Nhà nước\" OR \"tỷ giá\" OR Vietnam regulation OR Cafef OR Vietstock OR VnEconomy"
    }

    # Simple in-memory cache with last_updated
    cache = { "articles": {}, "last_updated": None }

    def fetch_for_topic(topic_key, pageSize=30, language="en"):
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
        except Exception as e:
            return []

    def refresh_all():
        results = {}
        for k in TOPICS.keys():
            # fetch both en and vi
            en = fetch_for_topic(k, language="en")
            vi = fetch_for_topic(k, language="vi")
            merged = (en or []) + (vi or [])
            # simple dedupe by url
            seen = set(); dedup = []
            for it in merged:
                u = it.get("url")
                if not u or u in seen:
                    continue
                seen.add(u); dedup.append(it)
            results[k] = dedup
        cache["articles"] = results
        cache["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Background thread to refresh every 30 minutes
    def schedule_refresh(interval_minutes=30):
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
        # initial fetch
        try:
            refresh_all()
        except Exception:
            pass
        # start background refresher
        schedule_refresh(interval_minutes=30)

    @app.get("/articles")
    def get_articles(topic: str = "policy"):
        # topic can be: policy, fx, metals, investment, vietnam
        if topic not in TOPICS:
            raise HTTPException(status_code=400, detail="Invalid topic")
        return {
            "topic": topic,
            "last_updated": cache.get("last_updated"),
            "count": len(cache.get("articles", {}).get(topic, [])),
            "articles": cache.get("articles", {}).get(topic, [])
        }

    @app.get("/health")
    def health():
        return {"status": "ok", "last_updated": cache.get("last_updated")}
