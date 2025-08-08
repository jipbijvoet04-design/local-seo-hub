
# Local SEO Rank Hub (Streamlit)

A browser-based Google Maps rank checker to track local rankings for keywords.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud
1. Push this folder to a **public GitHub repo**.
2. Go to https://share.streamlit.io → **New app** → select your repo.
3. App file: `app.py`  |  Python version: **3.11** (provided by `runtime.txt`).
4. In Streamlit Cloud → **App → Settings → Secrets**, add:
```
GOOGLE_PLACES_API_KEY = "your-key-here"
```
5. Deploy. You’ll get a URL like `https://yourname-yourrepo.streamlit.app`.
