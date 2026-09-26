"""Turn Jev's judgments into line items, totals, and a ranking of the three sources."""

from room_valuation import prices
from room_valuation.jev import CONDITION_LEVELS, Group
from room_valuation.schema import Item

REVIEW_CONFIDENCE = 0.5  # below this Jev confidence a line is flagged for a human


def _pick(answer, members: dict[str, Item]) -> tuple[str, float, dict]:
    probs = {k: float(v) for k, v in answer.probabilities.items()}
    return answer.choice, float(answer.confidence), probs


def line_items(groups: list[Group], answers: dict) -> list[dict]:
    lines = []
    for n, g in enumerate(groups):
        m = g.members
        flags = list(g.flags)
        # identity
        if f"id_{n}" in answers:
            id_src, id_conf, id_probs = _pick(answers[f"id_{n}"], m)
        else:
            id_src, id_conf, id_probs = next(iter(m)), None, {}
        item = m[id_src]
        # price
        if f"price_{n}" in answers:
            price_src, price_conf, price_probs = _pick(answers[f"price_{n}"], m)
        else:
            price_src = next((s for s, it in m.items() if it.rcv_inr), None)
            price_conf, price_probs = None, {}
        rcv = m[price_src].rcv_inr if price_src else None
        # condition, age
        condition = item.condition
        if f"cond_{n}" in answers:
            condition = CONDITION_LEVELS[max(0, min(3, round(answers[f"cond_{n}"].score)))]
        age = next((it.age_years for it in m.values() if it.age_years is not None), None)
        acv, acv_basis = prices.acv(rcv, item.category, age, condition) if rcv else (None, None)
        book = next((it.book for it in m.values() if it.book and it.book.title), None)
        genre = answers[f"genre_{n}"].choice if f"genre_{n}" in answers else (book.genre if book else None)
        for label, conf in (("identity", id_conf), ("price", price_conf)):
            if conf is not None and conf < REVIEW_CONFIDENCE:
                flags.append(f"low Jev confidence on {label} ({conf:.2f})")
        if rcv is None:
            flags.append("no price from any source")
        qty = item.quantity or 1
        lines.append({
            "n": n, "category": item.category, "name": item.name, "brand": item.brand, "model": item.model,
            "attributes": item.attributes, "quantity": qty, "condition": condition, "age_years": age,
            "book": ({**book.model_dump(), "genre": genre} if book else None),
            "sources": sorted(m), "identity_from": id_src, "identity_confidence": id_conf, "identity_probs": id_probs,
            "price_from": price_src, "price_confidence": price_conf, "price_probs": price_probs,
            "rcv_unit_inr": rcv, "rcv_inr": rcv * qty if rcv else None, "acv_inr": acv * qty if acv else None,
            "acv_basis": acv_basis, "price_source": m[price_src].price_source if price_src else None,
            "price_note": m[price_src].price_note if price_src else None,
            "candidates": {s: {"name": it.name, "brand": it.brand, "model": it.model, "rcv_inr": it.rcv_inr,
                               "price_source": it.price_source, "price_note": it.price_note, "photos": it.photos}
                           for s, it in m.items()},
            "photos": sorted({p for it in m.values() for p in it.photos}),
            "flags": flags,
        })
    return lines


def leaderboard(lines: list[dict]) -> dict:
    """How the sources ranked against each other across every contested decision."""
    board = {}
    for kind in ("identity", "price"):
        contested = [ln for ln in lines if ln[f"{kind}_probs"]]
        for src in ("local", "frontier", "voice"):
            took = [ln for ln in contested if src in ln[f"{kind}_probs"]]
            won = [ln for ln in took if ln[f"{kind}_from"] == src]
            board.setdefault(src, {})[kind] = {
                "contested": len(took), "chosen": len(won),
                "mean_probability": round(sum(ln[f"{kind}_probs"][src] for ln in took) / len(took), 3) if took else None,
            }
    for src in ("local", "frontier", "voice"):
        board[src]["items_found"] = sum(1 for ln in lines if src in ln["sources"])
        board[src]["found_alone"] = sum(1 for ln in lines if ln["sources"] == [src])
    return board


def totals(lines: list[dict]) -> dict:
    by_cat = {}
    for ln in lines:
        c = by_cat.setdefault(ln["category"], {"items": 0, "rcv_inr": 0.0, "acv_inr": 0.0})
        c["items"] += ln["quantity"]
        c["rcv_inr"] += ln["rcv_inr"] or 0
        c["acv_inr"] += ln["acv_inr"] or 0
    books = [ln for ln in lines if ln["category"] == "book"]
    return {
        "rcv_inr": round(sum(ln["rcv_inr"] or 0 for ln in lines)),
        "acv_inr": round(sum(ln["acv_inr"] or 0 for ln in lines)),
        "items": sum(ln["quantity"] for ln in lines),
        "unpriced": sum(1 for ln in lines if not ln["rcv_inr"]),
        "needs_review": sum(1 for ln in lines if ln["flags"]),
        "possible_double_count_inr": round(sum(ln["rcv_inr"] or 0 for ln in lines
                                               if any(f.startswith("possible double count") for f in ln["flags"]))),
        "books": {"count": len(books), "rcv_inr": round(sum(ln["rcv_inr"] or 0 for ln in books)),
                  "by_genre": _count(ln["book"]["genre"] for ln in books if ln["book"])},
        "by_category": {k: {**v, "rcv_inr": round(v["rcv_inr"]), "acv_inr": round(v["acv_inr"])}
                        for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1]["rcv_inr"])},
    }


def _count(values) -> dict:
    out = {}
    for v in values:
        out[v or "other"] = out.get(v or "other", 0) + 1
    return out
