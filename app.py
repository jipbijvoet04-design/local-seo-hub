import time
from typing import List, Dict, Tuple

import pandas as pd
import streamlit as st

from utils import text_search, find_positions

st.set_page_config(page_title="Local SEO Rank Checker", layout="wide")
st.title("Local SEO Rank Checker (Google Maps)")

with st.sidebar:
    st.header("Your business")
    api_key = st.text_input("Google Places API key", type="password", value=st.secrets.get("GOOGLE_PLACES_API_KEY", ""))
    your_name = st.text_input("Business name (label)", "Sporthuis Bijvoet")
    your_place_id = st.text_input("Business Place ID", "ChIJRfbsyIkNxkcRPb1TW3EG8Ao")

    st.header("Competitors (optional)")
    comp_inputs: List[Tuple[str, str]] = []
    for i in range(1, 5):
        col1, col2 = st.columns([1, 1.5])
        with col1:
            cname = st.text_input(f"Comp {i} name", value="" if i > 1 else "")
        with col2:
            cid = st.text_input(f"Comp {i} Place ID", value="")
        if cname.strip() or cid.strip():
            comp_inputs.append((cname.strip(), cid.strip()))

st.subheader("Keywords (max 5)")
default_keywords = "sportschool weesp\ngym weesp\npersonal trainer weesp\nbootcamp weesp\nfitness weesp"
kw_text = st.text_area("One per line", value=default_keywords, height=140)
keywords: List[str] = [k.strip() for k in kw_text.splitlines() if k.strip()][:5]  # hard limit 5

run_btn = st.button("Run check")

if run_btn:
    # Basic validation
    if not api_key:
        st.error("Add your Google Places API key in the sidebar.")
        st.stop()
    if not your_place_id and not your_name:
        st.error("Provide at least your business Place ID (recommended) or a clear name.")
        st.stop()
    if not keywords:
        st.error("Add at least one keyword (max 5).")
        st.stop()

    # Build the entity list in the order to display
    entities: List[Tuple[str, str]] = []
    entities.append((your_name or "You", your_place_id.strip()))
    for (n, pid) in comp_inputs:
        if n or pid:
            entities.append((n or "Competitor", pid))

    # Run per keyword: fetch once, compute positions for all entities
    rows: List[Dict[str, str]] = []
    for kw in keywords:
        results = text_search(
            query=kw,
            api_key=api_key,
            region="nl",
            language="nl",
            pagelimit=1  # fixed to 1 page (up to ~20 results)
        )
        pos_by_label = find_positions(results, entities)
        row = {"keyword": kw}
        row.update(pos_by_label)
        rows.append(row)
        time.sleep(1.0)  # fixed delay between keywords

    # Build dataframe with columns in the same order we constructed entities
    columns = ["keyword"] + [label for (label, _) in entities]
    df = pd.DataFrame(rows, columns=columns)

    st.success(f"Completed {len(df)} keyword checks.")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="results.csv",
        mime="text/csv"
    )

    st.caption("Notes: Place IDs ensure exact matching. If a cell is blank, the business was not found on the first page of results for that keyword.")
