"""Turn Jev's judgments into line items, totals, and a ranking of the three sources."""

from collections import Counter

from room_valuation import prices
from room_valuation.jev import CONDITION_LEVELS, Group, market_candidates
from room_valuation.schema import BUILDING, CATEGORY_DEFS

REVIEW_CONFIDENCE = 0.5  # below this Jev confidence a line is flagged for a human
HOLD_SPREAD = 3.0  # Jev unsure and the market prices this many times apart: no pick, held for review
OWNER_ABOVE_MARKET = 1.3  # an owner's price this far above the market price asks for a receipt
SOURCES = ("local", "frontier", "object", "voice", "market")
# where the model decides the price (a 3050 or a 5050 laptop, a 24 or a 27 inch monitor, a 1 or 1.5 ton AC)
MODEL_PRICED = {"laptop", "monitor", "phone", "audio", "networking", "appliance", "computer_accessory"}


def _pick(answer) -> tuple[str, float, dict]:
    probs = {k: float(v) for k, v in answer.probabilities.items()}
    return answer.choice, float(answer.confidence), probs


def line_items(groups: list[Group], answers: dict) -> list[dict]:
    lines = []
    for n, g in enumerate(groups):
        m = g.members
        flags = list(g.flags)
        # identity
        if f"id_{n}" in answers:
            id_src, id_conf, id_probs = _pick(answers[f"id_{n}"])
        else:
            id_src, id_conf, id_probs = next(iter(m)), None, {}
        item = m[id_src]
        if f"cat_{n}" in answers and answers[f"cat_{n}"].choice in CATEGORY_DEFS:  # Jev, from every reading
            item = item.model_copy(update={"category": answers[f"cat_{n}"].choice})
        # price: from the market candidates; the owner's figure is checked against it
        cands = market_candidates(g)
        if f"price_{n}" in answers:
            price_src, price_conf, price_probs = _pick(answers[f"price_{n}"])
        else:
            price_src = next(iter(cands), None)
            price_conf, price_probs = None, {}
        rcv = m[price_src].rcv_inr if price_src else None
        chosen = m[price_src] if price_src else None
        # condition, age
        condition = item.condition
        if f"cond_{n}" in answers:
            condition = CONDITION_LEVELS[max(0, min(3, round(answers[f"cond_{n}"].score)))]
        age = next((it.age_years for it in m.values() if it.age_years is not None), None)
        paid = next((it.price_paid_inr for it in m.values() if it.price_paid_inr), None)
        acv, acv_basis = prices.acv(rcv, item.category, age, condition) if rcv else (None, None)
        book = next((it.book for it in m.values() if it.book and it.book.title), None)
        genre = answers[f"genre_{n}"].choice if f"genre_{n}" in answers else (book.genre if book else None)
        for label, conf in (("identity", id_conf), ("price", price_conf)):
            if conf is not None and conf < REVIEW_CONFIDENCE:
                flags.append(f"low Jev confidence on {label} ({conf:.2f})")
        if rcv is None:
            flags.append("no price from any source")
        held = None
        spread = [it.rcv_inr for it in cands.values()]
        if price_conf is not None and price_conf < REVIEW_CONFIDENCE and len(spread) > 1 \
                and max(spread) >= HOLD_SPREAD * min(spread):
            held = {"low_inr": min(spread) * (item.quantity or 1), "high_inr": max(spread) * (item.quantity or 1),
                    "reason": f"Jev is unsure ({price_conf:.2f}) and the prices are {max(spread) / min(spread):.0f} "
                              f"times apart"}
            flags.append(f"held for review: {held['reason']}; not in the total")
        owner = m.get("voice")
        said = owner.rcv_inr if owner else None  # a recent purchase; an old price paid is not a replacement cost
        if price_src == "voice":
            flags.append("priced only by the owner's word: ask for a receipt")
        elif said and rcv and said > OWNER_ABOVE_MARKET * rcv:
            flags.append(f"the owner says Rs {said:,.0f}, {said / rcv - 1:.0%} above the market price: ask for a receipt")
        if chosen and item.category in MODEL_PRICED and chosen.price_kind != "exact" and not any(
                it.attributes.get("model_source") == "read off the label" for it in m.values()):
            flags.append("exact model not seen: priced as the closest equivalent; a close-up of its label, rating "
                         "plate or box gives the exact price")
        if item.category in prices.COMPUTERS and item.category != "computer_accessory":
            config = next((it.attributes for it in m.values() if it.attributes.get("cpu") or it.attributes.get("gpu")), None)
            if any(it.attributes.get("model_source") == "read off the label" for it in m.values()):
                config = config or {"spec_source": "the model number read off the label"}
            if not config:
                flags.append("configuration unknown (CPU, GPU, RAM): priced as the base model; a close-up of the bottom "
                             "label, the box or Settings > About gives the exact price")
            elif config.get("spec_source") == "the owner's words, to confirm":
                flags.append("priced with the configuration the owner stated: confirm it from a label or Settings > About")
        measured = next((it.measured for it in m.values() if it.measured), None)
        for src, it in m.items():  # the product's dimensions (from the web, or a listing) against the 3D measurement
            size = prices.listing_size(it.product_size) if it.product_size else None
            why = prices.size_mismatch(measured, size, item.category)
            if not why:
                continue
            flags.append(f"3D size check: the {src} source's product is {why}")
            # seen only in its own crop (not by the room pass, no owner note) and fitting nothing that size:
            # most likely not the object it was called (the blurred curtain called a wardrobe)
            alone = "frontier" not in m and "voice" not in m
            if src == price_src and alone and not held and (prices.size_ratio(measured, size) or 0) > 3:
                held = {"low_inr": 0, "high_inr": rcv * (item.quantity or 1),
                        "reason": f"seen only in its own crop, and the priced product ({it.product_size}) is over 3 times "
                                  f"the size measured in 3D"}
                flags.append(f"held for review: {held['reason']}; not in the total")
        free = next((it.attributes.get("acquired") for it in m.values() if it.attributes.get("acquired")), None)
        if free:
            flags.append(f"owner: {free}")
        qty = item.quantity or 1
        lines.append({
            "n": n, "key": "|".join(sorted(f"{s}:{it.id}" for s, it in m.items())),  # stable across replays
            "category": item.category, "name": item.name, "brand": item.brand, "model": item.model,
            "attributes": item.attributes, "quantity": qty, "condition": condition, "age_years": age, "price_paid_inr": paid,
            "book": ({**book.model_dump(), "genre": genre} if book else None),
            "sources": sorted(m), "identity_from": id_src, "identity_confidence": id_conf, "identity_probs": id_probs,
            "price_from": price_src, "price_confidence": price_conf, "price_probs": price_probs,
            "rcv_unit_inr": rcv, "rcv_inr": rcv * qty if rcv else None, "acv_inr": acv * qty if acv else None,
            "acv_basis": acv_basis, "price_source": chosen.price_source if chosen else None,
            "price_note": chosen.price_note if chosen else None,
            "price_kind": chosen.price_kind if chosen else None,
            "price_range_inr": ([chosen.price_low_inr * qty, chosen.price_high_inr * qty]
                                if chosen and chosen.price_low_inr and chosen.price_high_inr else None),
            "held": held, "owner_price_inr": owner.price_paid_inr if owner else None, "measured": measured,
            "candidates": {s: {"name": it.name, "brand": it.brand, "model": it.model, "rcv_inr": it.rcv_inr,
                               "price_source": it.price_source, "price_note": it.price_note, "photos": it.photos,
                               "price_kind": it.price_kind, "product_size": it.product_size,
                               "range_inr": [it.price_low_inr, it.price_high_inr] if it.price_low_inr else None,
                               "listings": [{k: li.get(k) for k in ("title", "price", "seller", "url", "verdict",
                                                                    "jev_score", "size", "size_mismatch")}
                                            for li in it.listings]}
                           for s, it in m.items()},
            "photos": sorted({p for it in m.values() for p in it.photos}),
            "flags": flags,
        })
    return lines


def suggest_duplicates(lines: list[dict]) -> None:
    """For a line flagged as a possible double count, the line it probably duplicates."""
    import re

    owner = {}
    for ln in lines:
        for part in ln["key"].split("|"):
            owner[part.split(":", 1)[1]] = ln["key"]
    for ln in lines:
        for f in ln["flags"]:
            m = re.search(r"\(([\w-]+)\)", f) if f.startswith("possible double count") else None
            if m and owner.get(m.group(1)) and owner[m.group(1)] != ln["key"]:
                ln["suggest_duplicate_of"] = owner[m.group(1)]
                break


def apply_review(lines: list[dict], review: dict) -> list[dict]:
    """The owner's last word on the result: a removed line, or a line marked as a duplicate of
    another, stays visible but leaves the totals. Returns the lines that count."""
    keys = {ln["key"] for ln in lines}
    kept = []
    for ln in lines:
        r = review.get(ln["key"])
        if r and (r["action"] == "remove" or (r["action"] == "duplicate" and r.get("of") in keys)):
            ln["review"] = r
        else:
            ln.pop("review", None)
            kept.append(ln)
    return kept


def reviewed_report(report: dict, review: dict) -> dict:
    """The report with the owner's review applied: totals and leaderboard from the kept lines."""
    lines = report["items"]
    suggest_duplicates(lines)
    kept = apply_review(lines, review or {})
    report["totals"] = totals(kept)
    report["review_summary"] = {"removed": sum(1 for ln in lines if ln.get("review", {}).get("action") == "remove"),
                                "duplicates": sum(1 for ln in lines if ln.get("review", {}).get("action") == "duplicate"),
                                "kept": len(kept)}
    return report


def leaderboard(lines: list[dict]) -> dict:
    """How the sources ranked against each other across every contested decision."""
    board = {}
    for kind in ("identity", "price"):
        contested = [ln for ln in lines if ln[f"{kind}_probs"]]
        for src in SOURCES:
            took = [ln for ln in contested if src in ln[f"{kind}_probs"]]
            won = [ln for ln in took if ln[f"{kind}_from"] == src]
            board.setdefault(src, {})[kind] = {
                "contested": len(took), "chosen": len(won),
                "mean_probability": round(sum(ln[f"{kind}_probs"][src] for ln in took) / len(took), 3) if took else None,
            }
    for src in SOURCES:
        board[src]["items_found"] = sum(1 for ln in lines if src in ln["sources"])
        board[src]["found_alone"] = sum(1 for ln in lines if ln["sources"] == [src])
    return board


def totals(lines: list[dict]) -> dict:
    """Held lines (valuation unsure, prices far apart) leave the sums and are reported apart,
    as the range of what they could add."""
    held = [ln for ln in lines if ln.get("held")]
    lines = [ln for ln in lines if not ln.get("held")]
    by_cat = {}
    for ln in lines:
        c = by_cat.setdefault(ln["category"], {"items": 0, "rcv_inr": 0.0, "acv_inr": 0.0})
        c["items"] += ln["quantity"]
        c["rcv_inr"] += ln["rcv_inr"] or 0
        c["acv_inr"] += ln["acv_inr"] or 0
    books = [ln for ln in lines if ln["category"] == "book"]
    contents = [ln for ln in lines if ln["category"] not in BUILDING]
    fixtures = [ln for ln in lines if ln["category"] in BUILDING]
    return {
        "contents": _sum(contents),
        "building_fixtures": _sum(fixtures),
        **_sum(lines),
        "unpriced": sum(1 for ln in lines if not ln["rcv_inr"]),
        "held_for_review": {"lines": len(held), "low_inr": round(sum(ln["held"]["low_inr"] for ln in held)),
                            "high_inr": round(sum(ln["held"]["high_inr"] for ln in held))},
        "needs_review": sum(1 for ln in lines if ln["flags"]) + len(held),
        "possible_double_count_inr": round(sum(ln["rcv_inr"] or 0 for ln in lines
                                               if any(f.startswith("possible double count") for f in ln["flags"]))),
        "books": {"count": len(books), "rcv_inr": round(sum(ln["rcv_inr"] or 0 for ln in books)),
                  "by_genre": dict(Counter(ln["book"]["genre"] or "other" for ln in books if ln["book"]))},
        "by_category": {k: {**v, "rcv_inr": round(v["rcv_inr"]), "acv_inr": round(v["acv_inr"])}
                        for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1]["rcv_inr"])},
    }


def _sum(lines: list[dict]) -> dict:
    return {"items": sum(ln["quantity"] for ln in lines), "rcv_inr": round(sum(ln["rcv_inr"] or 0 for ln in lines)),
            "acv_inr": round(sum(ln["acv_inr"] or 0 for ln in lines))}
