import time
from typing import List, Dict, Tuple, Optional

import pandas as pd
import streamlit as st

from utils import text_search, find_positions

# Nieuw: pytrends voor suggesties
from pytrends.request import TrendReq

st.set_page_config(page_title="Local SEO Rank Checker", layout="wide")
st.title("Local SEO Rank Checker (Google Maps)")

# ============ SIDEBAR INPUTS ============
with st.sidebar:
    st.header("Jouw bedrijf")
    api_key = st.text_input("Google Places API key", type="password", value=st.secrets.get("GOOGLE_PLACES_API_KEY", ""))
    your_name = st.text_input("Naam (label)", "Sporthuis Bijvoet")
    your_place_id = st.text_input("Place ID", "ChIJRfbsyIkNxkcRPb1TW3EG8Ao")

    st.header("Concurrenten (optioneel, max 4)")
    comp_inputs: List[Tuple[str, str]] = []
    for i in range(1, 5):
        col1, col2 = st.columns([1, 1.5])
        with col1:
            cname = st.text_input(f"Conc {i} naam", value="" if i > 1 else "")
        with col2:
            cid = st.text_input(f"Conc {i} Place ID", value="")
        if cname.strip() or cid.strip():
            comp_inputs.append((cname.strip(), cid.strip()))

# ============ KEYWORDS ============
st.subheader("Keywords (max 5)")

# Seed + suggesties
with st.expander("Automatische suggesties (optioneel)", expanded=True):
    col_a, col_b = st.columns([2,1])
    with col_a:
        seed = st.text_input("Seed keyword (bv. 'gym', 'sportschool')", value="gym")
    with col_b:
        suggest_btn = st.button("Haal suggesties (NL)")

default_keywords = "sportschool weesp\ngym weesp\npersonal trainer weesp\nbootcamp weesp\nfitness weesp"
kw_text = st.text_area("Één per regel", value=default_keywords, height=120)
keywords: List[str] = [k.strip() for k in kw_text.splitlines() if k.strip()][:5]  # hard limit 5

# Suggestie-actie
# Suggestie-actie (verbeterd met fallbacks)
if suggest_btn:
    try:
        pytrends = TrendReq(hl="nl-NL", tz=60)
        seed_clean = (seed or "").strip()

        candidates = []

        # 1) Probeer related_queries (top/rising) op NL
        if seed_clean:
            pytrends.build_payload([seed_clean], timeframe="today 12-m", geo="NL")
            related = pytrends.related_queries()
            for v in related.values():
                if v and "top" in v and isinstance(v["top"], pd.DataFrame):
                    candidates += v["top"]["query"].tolist()
                if v and "rising" in v and isinstance(v["rising"], pd.DataFrame):
                    candidates += v["rising"]["query"].tolist()

        # 2) Fallback: pytrends.suggestions (topics) → pak 'title'
        if not candidates and seed_clean:
            sugg = pytrends.suggestions(keyword=seed_clean) or []
            candidates += [item.get("title", "") for item in sugg if item.get("title")]

        # 3) Fallback: probeer simpele NL-varianten/synoniemen van de seed
        if not candidates and seed_clean:
            variants = {
                "nagelsalon": ["nagelsalon", "nagelstudio", "manicure", "pedicure", "acryl nagels", "gel nagels"],
                "gym": ["gym", "sportschool", "fitness", "personal trainer", "bootcamp"],
            }
            base = variants.get(seed_clean.lower(), [seed_clean, f"{seed_clean} salon", f"{seed_clean} studio"])
            # Vraag per variant related_queries op en voeg toe
            for term in base:
                try:
                    pytrends.build_payload([term], timeframe="today 12-m", geo="NL")
                    rel2 = pytrends.related_queries()
                    for v in rel2.values():
                        if v and "top" in v and isinstance(v["top"], pd.DataFrame):
                            candidates += v["top"]["query"].tolist()
                        if v and "rising" in v and isinstance(v["rising"], pd.DataFrame):
                            candidates += v["rising"]["query"].tolist()
                    # Kleine pauze tegen rate limiting
                    time.sleep(0.5)
                except Exception:
                    continue

        # Schoonmaken + dedupliceren
        seen = set()
        cleaned = []
        for q in candidates:
            qn = str(q).strip()
            if len(qn) < 2:
                continue
            key = qn.lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(qn)

        # Lokale intent: voeg 'weesp' toe als die er nog niet in staat
        localised = []
        for q in cleaned:
            if "weesp" not in q.lower():
                localised.append(f"{q} weesp")
            else:
                localised.append(q)

        # Max 5
        suggested = localised[:5] if localised else []
        if suggested:
            st.success("Suggesties bijgewerkt.")
            st.session_state["kw_text_override"] = "\n".join(suggested)
        else:
            st.info("Geen bruikbare NL-suggesties gevonden. Probeer een algemenere seed (bv. 'nagelstudio' of 'manicure').")
    except Exception as e:
        st.error(f"Suggesties ophalen mislukt: {e}")


# Als we suggesties hebben geplaatst, vervang de textarea inhoud éénmalig
if "kw_text_override" in st.session_state:
    kw_text = st.session_state.pop("kw_text_override")
    keywords = [k.strip() for k in kw_text.splitlines() if k.strip()][:5]

run_btn = st.button("Run check")

# ============ RUN CHECK ============
if run_btn:
    # Validatie
    if not api_key:
        st.error("Voer je Google Places API key in.")
        st.stop()
    if not your_place_id and not your_name:
        st.error("Geef minimaal je Place ID (aanbevolen) of een duidelijke naam.")
        st.stop()
    if not keywords:
        st.error("Voeg minimaal één keyword toe (max 5).")
        st.stop()

    # Entities in vaste volgorde
    entities: List[Tuple[str, str]] = []
    your_label = your_name or "Jij"
    entities.append((your_label, your_place_id.strip()))
    for (n, pid) in comp_inputs:
        if n or pid:
            entities.append((n or "Concurrent", pid))

    # Per keyword één fetch, dan posities bepalen voor alle entities
    rows: List[Dict[str, str]] = []
    for kw in keywords:
        results = text_search(
            query=kw,
            api_key=api_key,
            region="nl",
            language="nl",
            pagelimit=1  # 1 pagina (±20 resultaten)
        )
        pos_by_label = find_positions(results, entities)
        row = {"keyword": kw}
        row.update(pos_by_label)
        rows.append(row)
        time.sleep(1.0)  # vaste delay

    # Compacte tabel zonder kleur
    columns = ["keyword"] + [label for (label, _) in entities]
    df = pd.DataFrame(rows, columns=columns)

    st.success(f"Check voltooid voor {len(df)} keywords.")
    st.write("### Rankings")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="results.csv",
        mime="text/csv"
    )

    st.caption("Tip: gebruik Place IDs voor exacte matching. Lege cellen = niet gevonden op eerste pagina.")
