
import time
import json
import datetime as dt
from typing import List, Dict, Any, Optional

import requests

GOOGLE_PLACES_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

def text_search(query: str, api_key: str, location: Optional[str], radius: Optional[int], region: Optional[str], language: Optional[str], pagelimit: int = 2) -> List[Dict[str, Any]]:
    params = {"query": query, "key": api_key}
    if location:
        params["location"] = location
    if radius:
        params["radius"] = str(radius)
    if region:
        params["region"] = region
    if language:
        params["language"] = language

    all_results = []
    page = 0
    next_page_token = None

    while True:
        page += 1
        if next_page_token:
            params["pagetoken"] = next_page_token
            time.sleep(2)

        r = requests.get(GOOGLE_PLACES_TEXTSEARCH_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status", "")
        if status not in ("OK", "ZERO_RESULTS"):
            if status == "INVALID_REQUEST" and next_page_token:
                time.sleep(2)
                continue
            break

        results = data.get("results", [])
        all_results.extend(results)

        next_page_token = data.get("next_page_token")
        if not next_page_token or page >= pagelimit:
            break

    return all_results

def find_business_position(results: List[Dict[str, Any]], targets: List[str], target_place_id: Optional[str] = None) -> Optional[int]:
    targets_norm = [t.strip().lower() for t in targets if t.strip()]
    for idx, item in enumerate(results, start=1):
        name = (item.get("name") or "").strip().lower()
        place_id = item.get("place_id")
        if target_place_id and place_id == target_place_id:
            return idx
        if name and any(name == t or name.replace(" b.v.", "") == t for t in targets_norm):
            return idx
    return None

def run_keywords(api_key: str, target_names: List[str], keywords: List[str],
                 city_append: Optional[str], location: Optional[str], radius_m: Optional[int],
                 region: str, language: str, pagelimit: int, delay_sec: float,
                 target_place_id: Optional[str] = None) -> List[Dict[str, Any]]:
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    rows = []
    for kw in keywords:
        query = kw
        if city_append and city_append.lower() not in kw.lower():
            query = f"{kw} {city_append}"
        results = text_search(query=query, api_key=api_key, location=location, radius=radius_m, region=region, language=language, pagelimit=pagelimit)
        pos = find_business_position(results, targets=target_names, target_place_id=target_place_id)
        top10 = [{
            "name": r.get("name"),
            "place_id": r.get("place_id"),
            "rating": r.get("rating"),
            "user_ratings_total": r.get("user_ratings_total"),
            "formatted_address": r.get("formatted_address"),
        } for r in results[:10]]
        rows.append({
            "timestamp_utc": now,
            "keyword": kw,
            "query_sent": query,
            "position_maps": pos if pos is not None else "",
            "top10_snapshot_json": json.dumps(top10, ensure_ascii=False)
        })
        time.sleep(delay_sec)
    return rows
