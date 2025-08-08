import time
from typing import List, Dict, Any, Optional, Tuple

import requests

GOOGLE_PLACES_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

def text_search(
    query: str,
    api_key: str,
    region: Optional[str] = None,
    language: Optional[str] = None,
    pagelimit: int = 1,
) -> List[Dict[str, Any]]:
    """Fetch Google Places Text Search results for a query.
    We keep this minimal: region/language hints only, 1 page by default.
    """
    params = {"query": query, "key": api_key}
    if region:
        params["region"] = region
    if language:
        params["language"] = language

    all_results: List[Dict[str, Any]] = []
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

def _position_in_results(results: List[Dict[str, Any]], label: str, place_id: Optional[str], name_fallback: Optional[str]) -> Optional[int]:
    """Return 1-based position by exact place_id if provided; otherwise match by normalized name."""
    for idx, item in enumerate(results, start=1):
        if place_id and item.get("place_id") == place_id:
            return idx
    if name_fallback:
        target = name_fallback.strip().lower()
        for idx, item in enumerate(results, start=1):
            name = (item.get("name") or "").strip().lower()
            if name == target or name.replace(" b.v.", "") == target:
                return idx
    return None

def find_positions(results: List[Dict[str, Any]], entities: List[Tuple[str, str]]) -> Dict[str, Any]:
    """entities: list of (label, place_id). Returns mapping label -> position or ''."""
    out: Dict[str, Any] = {}
    for (label, pid) in entities:
        pos = _position_in_results(results, label=label, place_id=(pid or None), name_fallback=label)
        out[label] = pos if pos is not None else ""
    return out
