"""Write a capture's valuation to docs/results/<name>/: a readable report.md plus the
report.json and score.json it came from. Photos and video stay out of git.

    uv run python scripts/export_report.py <capture dir> <name>
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from room_valuation import score, session, valuation  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def inr(v) -> str:
    return "–" if v in (None, 0) else f"₹{v:,.0f}"


def label(ln: dict) -> str:
    if ln.get("book") and ln["name"] != "unidentified book":
        b = ln["book"]
        return f"{b['title']} ({b.get('author') or 'author not read'})"
    brand = ln.get("brand") or ""
    return ln["name"] if brand and ln["name"].lower().startswith(brand.lower()) else " ".join(x for x in (brand, ln["name"]) if x)


def main():
    cap, name = Path(sys.argv[1]), sys.argv[2]
    out = ROOT / "docs" / "results" / name
    out.mkdir(parents=True, exist_ok=True)
    rep = valuation.reviewed_report(json.loads((cap / "out" / "report.json").read_text()),
                                    session.load(cap).get("line_review") or {})
    truth_file = ROOT / "data" / "ground_truth" / "bedroom.json"
    sc = score.score(rep, json.loads(truth_file.read_text())) if truth_file.exists() else None
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    if sc:
        (out / "score.json").write_text(json.dumps(sc, indent=1, default=str))
    plan = (rep.get("area") or {}).get("plan_png")
    if plan and Path(plan).exists():
        shutil.copy(plan, out / "floor_plan.png")
    meta = json.loads((cap / "meta.json").read_text())
    s = session.load(cap)
    t, a = rep["totals"], rep.get("area") or {}

    L = [f"# {rep['room'].title()}, {rep['city']}: contents valuation", ""]
    L += [f"Capture `{cap.name}`" + (f", merged from {', '.join(meta['merged_from'])}" if meta.get("merged_from") else ""),
          f"- Photos: {len(s.get('photos') or [])} (room photos and video frames used for detection)",
          f"- Owner review: {rep.get('review', {}).get('kept')} items kept, {rep.get('review', {}).get('removed')} removed, "
          f"{rep.get('review', {}).get('added')} added, {rep.get('review', {}).get('closeups')} close-ups, "
          f"{rep.get('review', {}).get('voice_notes')} voice notes",
          f"- Pipeline 2: {rep['backend']}; Jev scored {rep['jev_pairs_scored']} pairs "
          f"(similarity filter skipped {rep.get('jev_pairs_skipped', 0)})",
          (f"- Market prices after Jev: {rep['market']['searched']} items searched on Serper, {rep['market']['priced']} priced, "
           f"{rep['market']['unreadable_books']} unreadable books at the room median" if rep.get("market") else ""), ""]
    L += ["## Totals", "", "| | Replacement (RCV) | After depreciation (ACV) | Items |", "|---|---|---|---|",
          f"| Contents (incl. books) | {inr(t['contents']['rcv_inr'])} | {inr(t['contents']['acv_inr'])} | {t['contents']['items']} |",
          f"| Building fixtures | {inr(t['building_fixtures']['rcv_inr'])} | {inr(t['building_fixtures']['acv_inr'])} | "
          f"{t['building_fixtures']['items']} |",
          f"| **Total** | **{inr(t['rcv_inr'])}** | **{inr(t['acv_inr'])}** | {t['items']} |", "",
          f"Books: {t['books']['count']}, {inr(t['books']['rcv_inr'])}. Lines flagged for review: {t['needs_review']}. "
          f"Possible double counts: {inr(t['possible_double_count_inr'])}."
          + (f" Owner's review: {rep['review_summary']['removed']} removed, {rep['review_summary']['duplicates']} marked duplicate."
             if rep.get("review_summary") else ""), ""]
    L += ["## Floor", ""]
    if a.get("area_m2"):
        L += [f"**{a['area_m2']} m² ({a['area_sqft']} sq ft)**, from {a['source']}"
              + (f"; {' x '.join(str(x) for x in a['dimensions_cm'])} cm" if a.get("dimensions_cm") else "")
              + (f", ceiling {a['ceiling_cm']} cm" if a.get("ceiling_cm") else ""), ""]
        for c in (a.get("candidates") or [])[1:]:
            L.append(f"- also {c['area_m2']} m² from {c['source']}")
        if (out / "floor_plan.png").exists():
            L += ["", "![floor plan](floor_plan.png)"]
    L += [""]
    L += ["## Items", "", "Price candidates: Local (pipeline 1's Serper search), Frontier (the frontier model's web price), Owner "
          "(a price paid within 2 years), Market (a second search after Jev, only for what was still unpriced). "
          "Price from: the one Jev trusted.", "",
          "| Item | Qty | RCV | ACV | Price from | Local | Frontier | Owner | Market | Flags |", "|---|---|---|---|---|---|---|---|---|---|"]
    rows = sorted(rep["items"], key=lambda ln: (ln["category"] == "book", ln["category"] in ("electrical_fixture", "building_fixture"),
                                               -(ln["rcv_inr"] or 0)))
    section = None
    for ln in rows:
        sec = "Books" if ln["category"] == "book" else "Building fixtures" if ln["category"] in (
            "electrical_fixture", "building_fixture") else "Contents"
        if sec != section:
            section = sec
            L.append(f"| **{sec}** | | | | | | | | | |")
        c = {k: v.get("rcv_inr") for k, v in ln["candidates"].items()}
        out_note = f"**{ln['review']['action']}** by owner" if ln.get("review") else ""
        flags = "; ".join(x for x in [out_note] + [f[:70] for f in ln["flags"][:2]] if x)
        genre = f" · {ln['book'].get('genre')}" if ln.get("book") and ln["name"] != "unidentified book" else ""
        L.append(f"| {label(ln)[:70]}{genre} | {ln['quantity']} | {inr(ln['rcv_inr'])} | {inr(ln['acv_inr'])} | "
                 f"{ln['price_from'] or '–'} | {inr(c.get('local'))} | {inr(c.get('frontier'))} | {inr(c.get('voice'))} | {inr(c.get('market'))} | {flags} |")
    L += [""]
    if sc:
        L += ["## Against the owner's ground truth", "", sc["summary"], "",
              "| Owner's item | Paid | Age (y) | Local | Frontier | Owner | Market | Chosen | RCV | Error |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in sc["items"]:
            c = r.get("candidates_inr") or {}
            err = f"{r['rcv_error_pct']:+.1f}%" if r.get("rcv_error_pct") is not None else ("not found" if not r["found"] else "–")
            L.append(f"| {r['truth']} | {inr(r['paid_inr'])} | {r['age_years'] if r['age_years'] is not None else '–'} | "
                     f"{inr(c.get('local'))} | {inr(c.get('frontier'))} | {inr(c.get('voice'))} | {inr(c.get('market'))} | {r.get('chosen_from') or '–'} | "
                     f"{inr(r.get('rcv_inr'))} | {err} |")
        L += ["", "Error is only computed where the purchase is within 2 years, so the price paid is a fair replacement cost."]
    lb = rep["leaderboard"]
    L += ["", "## How the sources ranked (Jev)", "", "| Source | Items found | Found alone | Identity chosen | Price chosen |",
          "|---|---|---|---|---|"]
    for src, v in lb.items():
        L.append(f"| {src} | {v['items_found']} | {v['found_alone']} | {v['identity']['chosen']}/{v['identity']['contested']} | "
                 f"{v['price']['chosen']}/{v['price']['contested']} |")
    (out / "report.md").write_text("\n".join(L) + "\n")
    print(out / "report.md")


if __name__ == "__main__":
    main()
