import time
from typing import List, Dict, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st

from utils import text_search, find_positions

st.set_page_config(page_title="Local SEO Rank Checker", layout="wide")
st.title("Local SEO Rank Checker (Google Maps)")

# ============ SIDEBAR INPUTS ============
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

# ============ RUN CHECK ============
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

    # Entities to score, in display order
    entities: List[Tuple[str, str]] = []
    your_label = your_name or "You"
    entities.append((your_label, your_place_id.strip()))
    for (n, pid) in comp_inputs:
        if n or pid:
            entities.append((n or "Competitor", pid))

    # Fetch results once per keyword and compute positions for all entities
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

    # Build dataframe with consistent column order
    columns = ["keyword"] + [label for (label, _) in entities]
    df = pd.DataFrame(rows, columns=columns)

    st.success(f"Completed {len(df)} keyword checks.")

    # ============ TABLE WITH CONDITIONAL COLORS ============
    def color_rank(val: Optional[object]) -> str:
        # Blank or NaN
        if val is None or (isinstance(val, float) and np.isnan(val)) or val == "":
            return "background-color: #ffe5e5"  # light red for not found
        try:
            v = int(val)
        except Exception:
            return ""
        if 1 <= v <= 3:
            return "background-color: #d6f5d6"  # green
        if 4 <= v <= 10:
            return "background-color: #fff4cc"  # yellow
        return "background-color: #ffe5e5"      # red-ish for >10

    # Apply styling (don’t color the keyword column)
    numeric_cols = [c for c in df.columns if c != "keyword"]
    styler = df.style.applymap(color_rank, subset=numeric_cols)
    st.write("### Keyword rankings")
    st.dataframe(styler, use_container_width=True)

    # ============ MINI DASHBOARD METRICS ============
    # Convert positions to numeric for summaries
    df_num = df.copy()
    for c in numeric_cols:
        df_num[c] = pd.to_numeric(df_num[c], errors="coerce")

    # Top-3 coverage per business
    coverage = {c: int((df_num[c].dropna() <= 3).sum()) for c in numeric_cols}
    cov_df = pd.DataFrame({"Business": list(coverage.keys()), "Top 3 count": list(coverage.values())}).set_index("Business")

    st.write("### Top-3 coverage (per business)")
    st.bar_chart(cov_df)

    # Average rank badges per business
    st.write("### Average rank (lower is better)")
    cols = st.columns(len(numeric_cols))
    for i, c in enumerate(numeric_cols):
        avg = df_num[c].mean(skipna=True)
        label = c
        if pd.isna(avg):
            cols[i].metric(label=label, value="—")
        else:
            cols[i].metric(label=label, value=f"{avg:.2f}")

    # Best keyword for your business
    st.write("### Best keyword for your business")
    best_kw = None
    best_pos = None
    if your_label in df_num.columns:
        series = df_num[your_label]
        if series.notna().any():
            best_pos = int(series.min())
            best_kw = df.loc[series.idxmin(), "keyword"]
    if best_kw is not None and best_pos is not None:
        st.success(f"Best keyword: **{best_kw}** — Rank **#{best_pos}**")
    else:
        st.info("No best keyword to highlight (not found in first page).")

    # Download
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="results.csv",
        mime="text/csv"
    )

    st.caption("Notes: Top-3 (green), 4–10 (yellow), >10 or not found (red). Place IDs ensure exact matching.")
