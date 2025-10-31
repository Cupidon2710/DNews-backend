DNews Backend (FastAPI)
-----------------------
- Endpoint: /articles?topic=policy|fx|metals|investment|vietnam
- Uses NEWSAPI_KEY environment variable (NewsAPI.org)
- Background refresher runs every 30 minutes to cache articles used by the frontend

Run locally:
  python -m venv .venv
  source .venv/bin/activate   # or .\.venv\Scripts\activate on Windows
  pip install -r requirements.txt
  export NEWSAPI_KEY=your_key_here
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
