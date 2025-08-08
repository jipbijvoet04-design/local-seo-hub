
import io
import json
from datetime import datetime
from typing import List

import pandas as pd
import streamlit as st

from utils import run_keywords

st.set_page_config(page_title="Local SEO Rank Hub", layout="wide")
st.title("Local SEO Rank Hub (Google Maps)")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Google Places API key", type="password", value=st.secrets.get("GOOGLE_PLACES_API_KEY", ""))
    business_name = st.text_input("Business Name (exact)", "Sporthuis Bijvoet")
    alt_names = st.text_input("Extra name variants (comma-separated)", "Sporthuisbijvoet")
    place_id = st.text_input("Place ID (recommended)", "ChIJRfbsyIkNxkcRPb1TW3EG8Ao")
    city_append = st.text_input("Append city (optional)", "weesp")
    location_bias = st.text_input("Location bias lat,lng (optional)", "52.3070,5.0416")
    radius_m = st.number_input("Radius (meters)", min_value=0, value=8000, step=500)
    region = st.text_input("Region (ccTLD)", "nl")
    language = st.text_input("Language", "nl")
    pagelimit = st.slider("Pages to scan (x20 results)", 1, 3, 2)
    delay_sec = st.slider("Delay between keywords (sec)", 0.0, 3.0, 1.0, 0.5)

st.subheader("Keywords")
default_keywords = "sportschool weesp\ngym weesp\npersonal trainer weesp\nbootcamp weesp\nfitness weesp"
kw_text = st.text_area("One per line", value=default_keywords, height=160)
keywords: List[str] = [k.strip() for k in kw_text.splitlines() if k.strip()]

run_btn = st.button("Run check")

if run_btn:
    if not api_key:
        st.error("Please paste your Google Places API key in the sidebar (or add it to Streamlit secrets).")
        st.stop()
    target_names = [business_name.strip()] + [s.strip() for s in alt_names.split(",") if s.strip()]
    rows = run_keywords(
        api_key=api_key,
        target_names=target_names,
        keywords=keywords,
        city_append=city_append if city_append else None,
        location=location_bias if location_bias else None,
        radius_m=int(radius_m) if radius_m else None,
        region=region or "nl",
        language=language or "nl",
        pagelimit=int(pagelimit),
        delay_sec=float(delay_sec),
        target_place_id=place_id if place_id else None
    )
    df = pd.DataFrame(rows, columns=["timestamp_utc","keyword","query_sent","position_maps","top10_snapshot_json"])
    st.success(f"Completed {len(df)} keyword checks.")
    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name=f"results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}Z.csv", mime="text/csv")
