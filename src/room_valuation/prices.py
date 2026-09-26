"""Live Indian prices for whatever the pipeline found, plus RCV to ACV depreciation.

Nothing is priced ahead of time: every item is searched at run time, so a new room with
new things works the same way. Two searches per item:
- Google Shopping, India: listings from Amazon.in, Flipkart, Croma, Reliance and others
- Google web search restricted to blinkit.com and zeptonow.com: quick-commerce product pages
  (both block direct scripted access, so their indexed pages are the legitimate route)
Provider: Serper.dev (2,500 free searches, no card), SERPER_API_KEY. Every query is cached on
disk, so reruns cost nothing.
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
    "appliance": 8, "lighting": 5, "electrical_fixture": 15, "building_fixture": 30, "furniture": 10, "bedding": 5,
    "book": 10, "decor": 10, "kitchenware": 5, "bag_clothing": 3, "other": 5,
}
CONDITION_LIFE_USED = {"like_new": 0.1, "good": 0.35, "fair": 0.6, "poor": 0.85}
SALVAGE_FLOOR = 0.10


def provider() -> str | None:
    """Part of every cache key, so a saved search stays valid across code changes."""
    return "serper" if os.environ.get("SERPER_API_KEY") else None


def _cached(kind: str, query: str, fetch) -> dict:
    """Disk cache keyed by provider, search kind and query."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = json.dumps({"p": provider(), "k": kind, "q": query}, sort_keys=True)
    f = CACHE / f"{hashlib.sha1(key.encode()).hexdigest()[:16]}.json"
    if f.exists():
        return json.loads(f.read_text())
    data = fetch()
    if data and "error" not in data:
        f.write_text(json.dumps({"query": query, "kind": kind, "provider": provider(), **data}))
    return data


def _serper(endpoint: str, query: str, attempts: int = 3) -> dict:
    """Up to three tries with a short backoff; a failure comes back as {"error"} and is not cached."""
    import time

    last = ""
    for i in range(attempts):
        try:
            r = httpx.post(f"https://google.serper.dev/{endpoint}", timeout=20,
                           headers={"X-API-KEY": os.environ["SERPER_API_KEY"], "Content-Type": "application/json"},
                           json={"q": query, "gl": "in", "hl": "en", "num": 20})
            if r.status_code == 200:
                return r.json()
            last = f"serper {r.status_code}: {r.text[:200]}"
            if r.status_code < 500 and r.status_code != 429:
                break
        except httpx.HTTPError as e:
            last = f"serper {type(e).__name__}"
        time.sleep(1.5 * (i + 1))
    return {"error": last}


def _rupees(text: str) -> list[float]:
    return [float(m.replace(",", "")) for m in re.findall(r"(?:₹|Rs\.?|INR)\s?([\d,]{2,9}(?:\.\d+)?)", text or "")]


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 1}


def shopping(query: str, limit: int = 20) -> list[dict]:
    """Google Shopping listings for India: [{title, price, seller, url}]."""
    if not provider():
        return []
    rows = _cached("shopping", query, lambda: _serper("shopping", query)).get("shopping") or []
    pairs = [(r, (_rupees(r.get("price", "")) or [None])[0]) for r in rows]
    return [{"title": r.get("title"), "price": float(price), "seller": r.get("source"), "url": r.get("link"),
             "engine": "serper shopping"} for r, price in pairs[:limit] if price]


def quick_commerce(query: str) -> list[dict]:
    """Blinkit and Zepto product pages that Google indexed with a price."""
    q = f"{query} ({' OR '.join(f'site:{s}' for s in QUICK_COMMERCE)})"
    if not provider():
        return []
    rows = _cached("site_search", q, lambda: _serper("search", q)).get("organic") or []
    out = []
    for r in rows:
        extra = {k: v for k, v in r.items() if k not in ("title", "link", "snippet")}
        prices = _rupees(" ".join([r.get("title", ""), r.get("snippet", ""), json.dumps(extra, ensure_ascii=False)]))
        seller = next((s for s in QUICK_COMMERCE if s in (r.get("link") or "")), None)
        if prices and seller:
            out.append({"title": r.get("title"), "price": prices[0], "seller": seller, "url": r.get("link"),
                        "engine": "serper site search"})
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


# a one-word name searches badly ("switch" matched Nintendo Switch listings, 2026-09-26): the
# category word keeps a vague query in the right aisle
CATEGORY_HINT = {"electrical_fixture": "electrical wall", "lighting": "LED", "computer_accessory": "computer",
                 "networking": "wifi", "appliance": "home appliance", "audio": "audio", "bedding": "bed",
                 "kitchenware": "kitchen", "decor": "home decor", "building_fixture": "house"}


def query_for(item) -> tuple[str, list[str]]:
    """Search text, and the words a listing title must contain (the brand)."""
    if item.category == "book" and item.book and item.book.title:
        return f"{item.book.title} {item.book.author or ''} paperback".strip(), []
    parts = [item.brand, item.model, item.attributes.get("size"), item.name]
    seen, words = set(), []
    for w in " ".join(p for p in parts if p).split():  # "Acer" + "Acer 24 inch monitor" says Acer once
        if w.lower() not in seen:
            seen.add(w.lower())
            words.append(w)
    name = " ".join(words)
    hint = CATEGORY_HINT.get(item.category)
    if len(words) <= 2 and hint and not set(hint.lower().split()) & seen:
        name = f"{name} {hint}"
    must = [item.brand.split()[0]] if item.brand else []
    return name, must


def lookup(item) -> tuple[float | None, str | None, str | None, dict]:
    """One search for an item: (price, url, note, raw result). A failed lookup costs one price."""
    q, must = query_for(item)
    try:
        p = price_item(q, item.category, must)
    except Exception as e:
        p = {"query": q, "rcv_inr": None, "note": f"price lookup failed: {type(e).__name__}"}
    if not p.get("rcv_inr"):
        return None, None, p.get("note"), p
    note = f"median of {p['matched']} matching listings for '{q}'" + (f" ({', '.join(p['sellers'])})" if p.get("sellers") else "")
    return p["rcv_inr"], p.get("url"), note, p
