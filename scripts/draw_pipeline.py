"""Draw docs/design/pipeline.png, the pipeline diagram. Rerun after changing the pipeline:

    uv run python scripts/draw_pipeline.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "design" / "pipeline.png"
INK, MUTED, LINE = "#16181d", "#475467", "#98a2b3"
FILL = {"input": "#eef4ff", "owner": "#fdf2fa", "local": "#ecfdf3", "frontier": "#fff6ed", "jev": "#f4f3ff",
        "value": "#f0f9ff", "store": "#f9fafb"}


def box(ax, x, y, w, h, title, body, kind):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012",
                                fc=FILL[kind], ec=LINE, lw=1.2, zorder=1))
    ax.text(x + 0.012, y + h - 0.010, title, fontsize=11.5, fontweight="bold", color=INK, va="top", ha="left", zorder=3)
    ax.text(x + 0.012, y + h - 0.032, body, fontsize=8.6, color=MUTED, va="top", ha="left", linespacing=1.45, zorder=3)


def arrow(ax, x0, y0, x1, y1, text=None):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=16, color=MUTED, lw=1.4,
                                 zorder=5, shrinkA=0, shrinkB=0))
    if text:
        ax.text((x0 + x1) / 2 + 0.008, (y0 + y1) / 2, text, fontsize=8, color=MUTED, va="center")


def main():
    fig = plt.figure(figsize=(15, 19), dpi=130)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.03, 0.985, "Room valuation pipeline", fontsize=20, fontweight="bold", color=INK, va="top")
    ax.text(0.03, 0.962, "phone capture  >  item list  >  three sources in parallel  >  Jev  >  valuation  >  owner review",
            fontsize=10.5, color=MUTED, va="top")

    # 1. inputs
    box(ax, 0.03, 0.855, 0.29, 0.085, "Room photos", "8 to 12 shots turning round the room\nEXIF-upright, at most 2048 px", "input")
    box(ax, 0.355, 0.855, 0.29, 0.085, "Room video (optional)",
        "30 to 60 s turnaround, ffmpeg 2 frames a second\nblurriest third dropped (Laplacian), up to 16 kept", "input")
    box(ax, 0.68, 0.855, 0.29, 0.085, "Room details", "room, city (local prices)\ntape length x width, or a measured floor plan", "input")
    for x in (0.175, 0.5, 0.825):
        arrow(ax, x, 0.851, x, 0.824)

    # 2. detection and review
    box(ax, 0.03, 0.725, 0.94, 0.095, "Step 2: detect, then the owner reviews the list",
        "OWLv2 over a general household vocabulary (all photos and frames)  >  Qwen3-VL-2B identifies each crop (category, name, readable brand/model)\n"
        "same object across photos merged (box containment in one photo, name and brand across photos); book boxes become one 'books' card\n"
        "owner removes false or duplicate items and adds what was missed   (web: /c/<id>)", "owner")
    arrow(ax, 0.5, 0.721, 0.5, 0.697)

    # 3. per item pages
    box(ax, 0.03, 0.605, 0.94, 0.088, "Step 3: one page per item, most valuable first",
        "close-ups: model sticker, label, book spines   |   any number of voice notes   |   a typed note   (web: /c/<id>/i/<item>)\n"
        "all notes on an item are read together as one owner statement   >   'Value the room'", "owner")
    for x in (0.18, 0.5, 0.82):
        arrow(ax, x, 0.601, x, 0.574)

    # 4. three sources
    box(ax, 0.03, 0.385, 0.295, 0.185, "Pipeline 1: local models (GPU)",
        "close-ups: PP-OCR (RapidOCR) + Qwen3-VL read\nbrand, model, specs off labels\n\n"
        "books: spines read at 0/90/270 deg, one band per\nspine, VLM cross-check needs OCR support,\n"
        "Open Library match needs title coverage\n\n"
        "prices: Serper Google Shopping India +\nBlinkit/Zepto site search, median of matching\nlistings, every query cached", "local")
    box(ax, 0.3525, 0.385, 0.295, 0.185, "Pipeline 2: frontier model",
        "Claude Opus 5.5 via claude -p (Read, WebSearch,\nWebFetch; no Bash or writes), or GPT-6 Astra\n(Responses API, web_search)\n\n"
        "reads every photo and close-up, dedupes,\nreads spines, counts switchboard modules,\n"
        "prices each item new in India with a URL,\nestimates area and shelves, notes risks", "frontier")
    box(ax, 0.675, 0.385, 0.295, 0.185, "Owner: voice and text",
        "Whisper large-v3-turbo (ffmpeg decode,\nany phone format)\n\n"
        "rules, not the model, read prices ('16K',\n'1.9 lakhs', 'Rs 2500') and ages ('3 years back',\n'one month old'); 'free' / 'provided' flagged\n\n"
        "a price paid counts as replacement cost only\nif bought within 2 years; Qwen reads brand", "owner")
    ax.text(0.5, 0.370, "the three run in parallel: the frontier model is remote; GPU work is one job at a time (file lock)",
            fontsize=8.5, color=MUTED, ha="center", va="center", zorder=6,
            bbox={"fc": "white", "ec": "none", "pad": 1.5})
    for x in (0.18, 0.5, 0.82):
        arrow(ax, x, 0.381, x, 0.354)

    # 5. Jev
    box(ax, 0.03, 0.2, 0.94, 0.15, "Jev (TypeSafe, jev-1.13): which items are the same, and which reading to trust",
        "links first: an owner's voice or typed note is tied to its item; a frontier item that lists an item's close-up (same category, shared word) is that item\n"
        "similarity filter: only each item's 3 most similar comparable-category candidates per other source are scored (334 of 452 pairs skipped on the merged capture)\n"
        "one Score per pair with spelled-out levels (different / possibly / same; books: same title allowing OCR slips)\n"
        "merge rules in code: Jev says same | possibly + mutual best | one of the category per source | same brand in the same photo; never two items from one source\n"
        "per merged item: Choice identity, Choice price (a recent owner price counts most), Score condition, Choice genre; confidence < 0.5 flags the line\n"
        "all questions batched (40 per call, 6 in parallel): 246 questions in 7 calls, 88k input tokens, about 5 s", "jev")
    arrow(ax, 0.26, 0.196, 0.26, 0.174)

    # 6. valuation and review
    box(ax, 0.03, 0.06, 0.45, 0.11, "Valuation",
        "RCV: chosen price x quantity\nACV: straight line over a per-category useful life, 10% salvage floor\n"
        "contents vs building fixtures (doors, windows, switchboards)\nbooks by genre, possible double counts, lines to review\n"
        "area: tape > measured floor plan > photo floor plan > frontier", "value")
    box(ax, 0.52, 0.06, 0.45, 0.11, "Results page and the owner's final review",
        "every line with what each source said and which one Jev trusted\n"
        "Remove / Same as (suggested duplicates) / Undo: totals recompute, no re-run,\nkept across replays   (web: /r/<id>)\n"
        "report.json, out/runs/<time>/ with every Jev call, settings and the score", "value")
    arrow(ax, 0.484, 0.115, 0.516, 0.115)

    ax.text(0.03, 0.035, "Replays: frontier.json, local_refined.json, transcripts.json and the Serper cache let "
            "`room-valuation revalue --reuse frontier,refine,transcripts` re-run Jev and the valuation in about a minute, for free.",
            fontsize=9, color=MUTED, va="top")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor="white")
    print(OUT)


if __name__ == "__main__":
    main()
