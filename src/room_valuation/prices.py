"""Live Indian prices for whatever the pipeline found, plus RCV to ACV depreciation.

Nothing is priced ahead of time: every item is searched at run time, so a new room with
new things works the same way. Sources, through SerpAPI:
- google_shopping with gl=in: listings from Amazon.in, Flipkart, Croma, Reliance and others
- google web search restricted to blinkit.com and zeptonow.com: quick-commerce product pages
  (both block direct scripted access, so their indexed pages are the legitimate route)
Every query is cached on disk; the free SerpAPI plan is 250 searches a month.
"""

import hashlib
import json
import os
import re
import statistics
from pathlib import Path

import httpx

CACHE = Path(__file__).resolve().parents[2] / "data" / "price_cache"
QUICK_COMMERCE = ["blinkit.com", "zeptonow.com"]
QC_CATEGORIES = {"computer_accessory", "audio", "phone", "lighting", "kitchenware", "appliance", "decor",
                 "bag_clothing", "networking", "electrical_fixture", "bedding"}

# insurance-style useful life by category, for straight-line depreciation (years)
USEFUL_LIFE = {
    "laptop": 5, "monitor": 6, "computer_accessory": 4, "phone": 4, "audio": 5, "networking": 5,
    "appliance": 8, "lighting": 5, "electrical_fixture": 15, "furniture": 10, "bedding": 5,
    "book": 10, "decor": 10, "kitchenware": 5, "bag_clothing": 3, "other": 5,
}
CONDITION_LIFE_USED = {"like_new": 0.1, "good": 0.35, "fair": 0.6, "poor": 0.85}
SALVAGE_FLOOR = 0.10


def _serpapi(params: dict) -> dict:
    key = os.environ.get("SERPAPI_API_KEY")
    CACHE.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
    cached = CACHE / f"{digest}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    if not key:
        return {"error": "SERPAPI_API_KEY not set"}
    r = httpx.get("https://serpapi.com/search.json", params={**params, "api_key": key}, timeout=30)
    data = r.json()
    if "error" not in data:
        cached.write_text(json.dumps({"params": params, **data}))
    return data


def _rupees(text: str) -> list[float]:
    return [float(m.replace(",", "")) for m in re.findall(r"(?:₹|Rs\.?|INR)\s?([\d,]{2,9}(?:\.\d+)?)", text or "")]


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 1}


def shopping(query: str, limit: int = 20) -> list[dict]:
    data = _serpapi({"engine": "google_shopping", "q": query, "gl": "in", "hl": "en", "location": "India"})
    out = []
    for r in (data.get("shopping_results") or [])[:limit]:
        price = r.get("extracted_price") or (_rupees(r.get("price", "")) or [None])[0]
        if price:
            out.append({"title": r.get("title"), "price": float(price), "seller": r.get("source"),
                        "url": r.get("product_link") or r.get("link"), "engine": "google_shopping"})
    return out


def quick_commerce(query: str) -> list[dict]:
    sites = " OR ".join(f"site:{s}" for s in QUICK_COMMERCE)
    data = _serpapi({"engine": "google", "q": f"{query} ({sites})", "gl": "in", "hl": "en", "num": 10})
    out = []
    for r in data.get("organic_results") or []:
        text = " ".join([r.get("title", ""), r.get("snippet", ""),
                         json.dumps(r.get("rich_snippet", {}))])
        prices = _rupees(text)
        if prices:
            seller = next((s for s in QUICK_COMMERCE if s in (r.get("link") or "")), r.get("source"))
            out.append({"title": r.get("title"), "price": prices[0], "seller": seller, "url": r.get("link"),
                        "engine": "google_site_search"})
    return out


def price_item(query: str, category: str, must_have: list[str] | None = None) -> dict:
    """Search, keep listings whose titles share enough words with the query, and take the
    median of the matches as the replacement cost. The median resists the accessory and
    bundle listings that shopping results always mix in."""
    listings = shopping(query)
    if category in QC_CATEGORIES:
        listings += quick_commerce(query)
    q = _tokens(query)
    need = {t.lower() for t in must_have or []}
    scored = []
    for li in listings:
        words = _tokens(li["title"])
        if need and not need <= words:
            continue
        overlap = len(q & words) / max(1, len(q))
        if overlap >= 0.5:
            scored.append({**li, "overlap": round(overlap, 2)})
    if not scored:
        return {"query": query, "rcv_inr": None, "listings": listings[:5], "matched": 0,
                "note": "no listing matched the item well enough"}
    price = statistics.median(li["price"] for li in scored)
    closest = min(scored, key=lambda li: abs(li["price"] - price))
    return {"query": query, "rcv_inr": round(price), "matched": len(scored), "url": closest["url"],
            "seller": closest["seller"], "listings": sorted(scored, key=lambda li: -li["overlap"])[:8],
            "sellers": sorted({li["seller"] for li in scored if li.get("seller")})}


def acv(rcv: float, category: str, age_years: float | None, condition: str | None) -> tuple[float, str]:
    """Actual cash value: straight-line depreciation over the category's useful life down to
    a 10 percent salvage floor. Age when the owner said it, otherwise visible condition."""
    life = USEFUL_LIFE.get(category, 5)
    if age_years is not None:
        used, basis = min(1.0, age_years / life), f"age {age_years:g} y of a {life} y life"
    else:
        used = CONDITION_LIFE_USED.get(condition or "good", 0.35)
        basis = f"condition '{condition or 'unknown'}' read as {used:.0%} of a {life} y life used"
    return round(rcv * max(SALVAGE_FLOOR, 1 - used)), basis
