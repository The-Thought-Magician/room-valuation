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

from room_valuation import specs

COMPUTERS = {"laptop", "phone", "computer_accessory"}  # priced by configuration
# PRICE_CACHE points a run at its own cache, e.g. an empty one to search everything afresh
CACHE = Path(os.environ.get("PRICE_CACHE") or Path(__file__).resolve().parents[2] / "data" / "price_cache")
QUICK_COMMERCE = ["blinkit.com", "zeptonow.com"]
QC_CATEGORIES = {"computer_accessory", "audio", "phone", "lighting", "kitchenware", "appliance", "decor",
                 "bag_clothing", "networking", "electrical_fixture", "bedding"}

# Straight-line depreciation as US contents adjusters apply it: age over the category's useful
# life, adjusted for condition, never past a cap. Sources (researched 2026-09-27):
# - Claims Pages' personal property depreciation guide (built with adjusters): useful lives by
#   category, and an item still working for its purpose is not depreciated past 90 percent.
# - Xactimate contents: a "max depreciation" setting per carrier and state, no published default.
# - Cozmo's CTO, 2026-09-26: "there's usually a depreciation cap, usually 75 to 80 percent".
# - California 10 CCR 2695.9: depreciation must be itemised and reflect a measurable loss of
#   value; labour is never depreciated (building fixtures are priced with installation, hence
#   their lower cap).
# The caps are defaults for a carrier's own table to replace. Books keep more value than
# electronics; adjusters often do not depreciate them at all.
# category: (useful life in years, most it may lose)
DEPRECIATION = {
    "laptop": (4, 0.80), "monitor": (6, 0.80), "computer_accessory": (4, 0.80), "phone": (3, 0.80),
    "audio": (5, 0.80), "networking": (5, 0.80), "appliance": (8, 0.75), "lighting": (7, 0.75),
    "electrical_fixture": (15, 0.70), "building_fixture": (30, 0.70), "furniture": (12, 0.75), "bedding": (5, 0.80),
    "book": (10, 0.50), "decor": (8, 0.75), "kitchenware": (7, 0.75), "bag_clothing": (3, 0.80), "other": (7, 0.80),
}
# no age given: the visible condition stands for how much of the life is used
CONDITION_LIFE_USED = {"like_new": 0.1, "good": 0.35, "fair": 0.6, "poor": 0.85}
# age given: condition moves the age-based rate (an old item kept like new loses less)
CONDITION_ADJUST = {"like_new": 0.75, "good": 1.0, "fair": 1.15, "poor": 1.3}


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


MAX_LISTINGS = 10  # listings kept per search for Jev to judge (jev.judge_listings)
# a replacement cost is the price new: second-hand listings are not candidates
USED = re.compile(r"\b(used|refurbished|renewed|pre-?owned|open[- ]box|second[- ]hand|unboxed)\b", re.I)


def quartiles(values: list[float]) -> tuple[float, float]:
    """25th and 75th percentile: the price range shown next to a median."""
    if len(values) < 2:
        return (values[0], values[0]) if values else (None, None)
    q = statistics.quantiles(sorted(values), n=4, method="inclusive")
    return round(q[0]), round(q[2])


def price_item(query: str, category: str, must_have: list[str] | None = None) -> dict:
    """Search, keep listings whose titles share enough words with the query, and take the
    median of the matches as the replacement cost, with the 25th to 75th percentile as its
    range. The median resists the accessory and bundle listings that shopping results always
    mix in. The best MAX_LISTINGS matches (a looser cut) are kept for Jev to judge one by one."""
    listings = shopping(query)
    if category in QC_CATEGORIES:
        listings += quick_commerce(query)
    q = _tokens(query)
    need = {t.lower() for t in must_have or []}
    scored = []
    for li in listings:
        words = _tokens(li["title"])
        if need and not need <= words or USED.search(li["title"] or ""):
            continue
        scored.append({**li, "overlap": round(len(q & words) / max(1, len(q)), 2), "size": listing_size(li["title"])})
    scored.sort(key=lambda li: -li["overlap"])
    matched = [li for li in scored if li["overlap"] >= 0.5]
    judge = [li for li in scored if li["overlap"] >= 0.34][:MAX_LISTINGS]
    if not matched:
        return {"query": query, "rcv_inr": None, "listings": judge, "matched": 0,
                "note": "no listing matched the item well enough"}
    price = statistics.median(li["price"] for li in matched)
    closest = min(matched, key=lambda li: abs(li["price"] - price))
    low, high = quartiles([li["price"] for li in matched])
    return {"query": query, "rcv_inr": round(price), "low": low, "high": high, "matched": len(matched),
            "url": closest["url"], "seller": closest["seller"], "listings": judge,
            "sellers": sorted({li["seller"] for li in matched if li.get("seller")})}


_UNIT_CM = {"cm": 1.0, "mm": 0.1, "m": 100.0, "in": 2.54, "inch": 2.54, "inches": 2.54, "ft": 30.48, "feet": 30.48}
_DIMS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:cm|mm|in|inch|ft|feet)?\s*[x×*]\s*(\d+(?:\.\d+)?)"
                   r"(?:\s*(?:cm|mm|in|inch|ft|feet)?\s*[x×*]\s*(\d+(?:\.\d+)?))?\s*(cm|mm|m|inches|inch|in|ft|feet)\b")
_DIAGONAL = re.compile(r"(\d{2}(?:\.\d)?)\s*(?:\"|”|''|-?\s?inch(?:es)?\b|in\b)")


def listing_size(title: str) -> dict | None:
    """The product's size as a listing title states it: '90 x 60 cm', '4x3 ft', '24 inch'."""
    t = (title or "").lower()
    m = _DIMS.search(t)
    if m:
        k = _UNIT_CM[m.group(4)]
        dims = sorted((float(x) * k for x in m.groups()[:3] if x), reverse=True)
        return {"dims_cm": [round(d) for d in dims]}
    m = _DIAGONAL.search(t)
    if m and 5 <= float(m.group(1)) <= 100:
        return {"diagonal_in": float(m.group(1))}
    return None


SIZE_TOLERANCE = 1.8  # measured sizes are estimates (geometry.py), so only a big gap counts


def size_mismatch(measured: dict | None, size: dict | None) -> str | None:
    """Why a product of this size cannot be the object measured in the room, or None."""
    if not measured or not size:
        return None
    w, h = measured["width_cm"], measured["height_cm"]
    if size.get("diagonal_in"):
        seen = (w * w + h * h) ** 0.5 / 2.54
        ratio = max(seen, size["diagonal_in"]) / max(1e-6, min(seen, size["diagonal_in"]))
        what = f"{size['diagonal_in']:g} inch against about {seen:.0f} inch measured"
    else:
        big, seen = size["dims_cm"][0], max(w, h)
        ratio = max(big, seen) / max(1e-6, min(big, seen))
        what = f"{'x'.join(str(d) for d in size['dims_cm'])} cm against about {w} x {h} cm measured"
    return what if ratio > SIZE_TOLERANCE else None


def acv(rcv: float, category: str, age_years: float | None, condition: str | None) -> tuple[float, str]:
    """Actual cash value: straight-line depreciation over the category's useful life, capped
    (DEPRECIATION). Age when the owner said it, adjusted for condition; otherwise the visible
    condition stands for the share of the life used."""
    life, cap = DEPRECIATION.get(category, DEPRECIATION["other"])
    if age_years is not None:
        adjust = CONDITION_ADJUST.get(condition or "good", 1.0)
        used = age_years / life * adjust
        basis = f"age {age_years:g} y of a {life} y life" + (f", condition {condition}" if adjust != 1.0 else "")
    else:
        used = CONDITION_LIFE_USED.get(condition or "good", 0.35)
        basis = f"condition '{condition or 'unknown'}' read as {used:.0%} of a {life} y life used"
    if used > cap:
        basis += f", capped at {cap:.0%} depreciation"
    return round(rcv * (1 - min(cap, max(0.0, used)))), basis


# a one-word name searches badly ("switch" matched Nintendo Switch listings, 2026-09-26): the
# category word keeps a vague query in the right aisle
CATEGORY_HINT = {"electrical_fixture": "electrical wall", "lighting": "LED", "computer_accessory": "computer",
                 "networking": "wifi", "appliance": "home appliance", "audio": "audio", "bedding": "bed",
                 "kitchenware": "kitchen", "decor": "home decor", "building_fixture": "house"}


def query_for(item) -> tuple[str, list[str]]:
    """Search text, and the words a listing title must contain (the brand)."""
    if item.category == "book" and item.book and item.book.title:
        return f"{item.book.title} {item.book.author or ''} paperback".strip(), []
    # a computer's configuration sets its price: 'HP Victus 15 Ryzen 7 260 RTX 5050', not 'HP Victus 15'
    config = specs.search_words(item.attributes) if item.category in COMPUTERS else ""
    parts = [item.brand, item.model, item.attributes.get("size"), item.name, config]
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
    gpu = re.search(r"\d{3,4}", item.attributes.get("gpu", "")) if item.category in COMPUTERS else None
    if gpu:  # a listing with another GPU is another price class
        must.append(gpu.group(0))
    return name, must


def model_number(item) -> str | None:
    """A model number read off the item's own label (local.refine checks the OCR shows it):
    letters and digits together, like 15-fb0136AX or HD9252."""
    if item.attributes.get("model_source") != "read off the label" or not item.model:
        return None
    toks = [t for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/]{3,}", item.model)
            if re.search(r"\d", t) and re.search(r"[A-Za-z]", t)]
    return max(toks, key=len) if toks else None


def lookup(item) -> tuple[float | None, str | None, str | None, dict]:
    """One search for an item: (price, url, note, raw result). With a model number read off the
    label it first searches that exact model, and only listings naming it count. A failed
    lookup costs one price."""
    exact = model_number(item)
    tries = []
    if exact:
        tries.append((f"{item.brand or ''} {exact}".strip(), sorted(_tokens(exact)), "exact"))
        if pid := item.attributes.get("product_id"):  # HP's product number: C28DWPA#ACJ is searched as C28DWPA
            code = re.split(r"[#/]", pid)[0]
            tries.append((f"{item.brand or ''} {code}".strip(), sorted(_tokens(code)), "exact"))
    q, must = query_for(item)
    tries.append((q, must, None))
    p = {}
    for query, need, kind in tries:
        try:
            p = {"query": query, **price_item(query, item.category, need), "kind": kind}
        except Exception as e:
            p = {"query": query, "rcv_inr": None, "note": f"price lookup failed: {type(e).__name__}"}
        if p.get("rcv_inr"):
            break
    if not p.get("rcv_inr"):
        return None, None, p.get("note"), p
    if p.get("kind") == "exact":  # what the listings of this exact model say its configuration is
        p["spec"] = specs.parse(" ".join(li["title"] or "" for li in p["listings"]), item.category)
    what = f"listings of model {exact}" if p.get("kind") == "exact" else "matching listings"
    note = f"median of {p['matched']} {what} for '{p['query']}'" + (f" ({', '.join(p['sellers'])})" if p.get("sellers") else "")
    return p["rcv_inr"], p.get("url"), note, p


def take(item, raw: dict) -> None:
    """Copy a lookup's range, kind and listings onto the item it priced."""
    item.price_low_inr, item.price_high_inr = raw.get("low"), raw.get("high")
    item.price_kind = raw.get("kind")
    item.listings = raw.get("listings") or []
    if raw.get("spec") and not (item.attributes.get("cpu") or item.attributes.get("gpu")):
        item.attributes |= raw["spec"] | {"spec_source": "listings of the exact model read off the label"}
