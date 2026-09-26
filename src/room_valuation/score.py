"""Score a report against the owner's ground truth (what they paid, from memory).

For each ground-truth item: the report line it matches (same category, most shared words),
what every source said it costs, what Jev chose, and the error against the price paid when
the purchase is recent enough for that to be a fair comparison. The pipeline never reads the
ground truth; this is only for tuning and for the write-up."""

import re

RECENT_YEARS = 2


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2}


def _match(truth: dict, lines: list[dict], used: set[int]) -> dict | None:
    cands = [ln for ln in lines if ln["category"] == truth["category"] and ln["n"] not in used]
    if not cands:
        return None
    tw = _words(truth["name"])

    def overlap(ln):
        text = " ".join([ln["name"], ln.get("brand") or "", ln.get("model") or ""]
                        + [c.get("name") or "" for c in ln["candidates"].values()])
        return (len(tw & _words(text)), ln["rcv_inr"] or 0)

    best = max(cands, key=overlap)
    return best if overlap(best)[0] > 0 else None


def score(report: dict, truth: dict) -> dict:
    lines, used, rows = report["items"], set(), []
    for t in truth["items"]:
        ln = _match(t, lines, used)
        if ln:
            used.add(ln["n"])
        paid, age = t.get("price_paid_inr"), t.get("age_years")
        fair = paid is not None and age is not None and age <= RECENT_YEARS
        row = {"truth": t["name"], "paid_inr": paid, "age_years": age, "found": ln is not None}
        if ln:
            row.update({
                "line": " ".join(x for x in (ln.get("brand"), ln["name"]) if x), "sources": ln["sources"],
                "candidates_inr": {s: c["rcv_inr"] for s, c in ln["candidates"].items()},
                "chosen_from": ln["price_from"], "rcv_inr": ln["rcv_inr"], "acv_inr": ln["acv_inr"],
                "price_confidence": ln["price_confidence"],
            })
            if fair and ln["rcv_inr"]:
                row["rcv_error_pct"] = round(100 * (ln["rcv_inr"] - paid) / paid, 1)
                row["per_source_error_pct"] = {s: round(100 * (v - paid) / paid, 1)
                                               for s, v in row["candidates_inr"].items() if v}
        rows.append(row)
    found = sum(r["found"] for r in rows)
    errs = [abs(r["rcv_error_pct"]) for r in rows if "rcv_error_pct" in r]
    summary = (f"{found}/{len(rows)} ground-truth items found; "
               f"{len(errs)} with a recent purchase price, mean |RCV error| "
               + (f"{sum(errs) / len(errs):.1f}%" if errs else "n/a"))
    return {"summary": summary, "items": rows,
            "report_totals": {k: report["totals"][k] for k in ("rcv_inr", "acv_inr", "items")}}
