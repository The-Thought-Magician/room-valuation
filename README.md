# Room valuation

A phone app that walks through a room and tells an insurer what it is worth:
- every object found and priced at local Indian prices
- every book read off its spine (title, author, genre, price)
- floor area, building fixtures (doors, windows, switchboards), and replacement and
  depreciated totals

There are three sources, and Jev combines them:

```
                    photos / video            close-ups, voice and typed notes per item
                          |                                  |
          +---------------+---------------+                  |
          v                               v                  v
  Pipeline 1: local models        Pipeline 2: frontier   Owner (voice + text)
  OWLv2 finds objects             Claude Opus 5.5 reads   Whisper transcribes,
  Qwen3-VL-2B identifies them     every photo and prices  rules read prices and ages,
  PP-OCR reads spines and labels  it with live web search Qwen reads brand and model
  Open Library: title, genre      (GPT-6 Astra adapter
  Serper: its own Indian price     written, see below)
          |                               |                  |
          +---------------+---------------+------------------+
                          v
        Jev (TypeSafe): which items are the same object,
        which description and which price to trust, condition, genre
                          v
        Market (Serper): anything still unpriced after Jev, searched
        once more with the identity Jev chose
                          v
        valuation: RCV and ACV per item, contents vs building fixtures,
        books by genre, possible double counts, lines for review
```

## Links

| What | Where |
|---|---|
| How every stage works (with a real Jev question and answer) | [docs/design/pipeline.md](docs/design/pipeline.md) |
| Pipeline diagram | [docs/design/pipeline.png](docs/design/pipeline.png), drawn by [scripts/draw_pipeline.py](scripts/draw_pipeline.py) |
| Result, merged capture (photos + video + close-ups + notes) | [docs/results/bedroom-merged/report.md](docs/results/bedroom-merged/report.md) |
| Result, photos capture | [docs/results/bedroom-photos/report.md](docs/results/bedroom-photos/report.md) |
| Result, video capture | [docs/results/bedroom-video/report.md](docs/results/bedroom-video/report.md) |
| Owner's ground truth (used only for scoring) | [data/ground_truth/bedroom.json](data/ground_truth/bedroom.json) |
| Project notes (brief, decisions, status) | [CLAUDE.md](CLAUDE.md) |
| Skills used in development (ponytail, MIT) | [.claude/skills/](.claude/skills/README.md) |

Each result folder has a readable `report.md`, plus `report.json`, `score.json` and
`floor_plan.png`.

## Web app

`scripts/serve.sh` starts the backend on http://127.0.0.1:8100 and a Cloudflare quick tunnel.
Open the printed `https://<name>.trycloudflare.com` address on the phone. The microphone needs
https, and the URL changes every time `serve.sh` restarts.

| Page | Path | What it does |
|---|---|---|
| Step 1: photos and/or video | [`/`](http://127.0.0.1:8100/) ([web/index.html](web/index.html)) | Room details (tape dimensions optional), room photos, a room video, or both. Then **Detect items** |
| Step 1, video only | [`/record`](http://127.0.0.1:8100/record) ([web/record.html](web/record.html)) | One button to film the room |
| Step 2: item list | `/c/<capture id>` ([web/items.html](web/items.html)) | Detected items counted by type. **Remove** false or duplicate ones, add what is missing, pick the frontier model, then **Walk through items** or **Value the room** |
| Step 3: one page per item | `/c/<capture id>/i/<item id>` ([web/item.html](web/item.html)) | Close-ups (labels, spines), any number of voice notes, a typed note, quantity |
| Results and final review | `/r/<capture id>` ([web/results.html](web/results.html)) | Totals, every item with every source's price and Jev's choice, books by genre, floor area and plan. **Remove**, **Same as** and **Undo** per line |
| Demo walkthrough | `/demo/<name>/` ([web/demo.html](web/demo.html)) | One real capture step by step: photos, video, detection boxes, the owner's list, close-ups and voice notes with transcripts, what each pipeline read, Jev's questions and answers, the valuation, the score. Built by `scripts/build_demo.py` |

The API behind the pages is in [src/room_valuation/server.py](src/room_valuation/server.py): `POST /api/captures`,
`/api/captures/<id>/session`, `/items/<item>`, `/items`, `/detect`, `/submit`, `/status`, `/report`, `/review`.

## Commands

Setup, once:

```
uv sync                                  # Python 3.14, torch 2.14 (CUDA 13)
cp .env.example .env                     # TYPESAFE_API_KEY, SERPER_API_KEY; OPENAI_API_KEY only for --backend astra
scripts/fetch_weights.sh                 # OWLv2, Qwen3-VL-2B, Whisper large-v3-turbo into the Hugging Face cache
claude                                   # pipeline 2 runs `claude -p`: log in to Claude Code once
```

Run the app:

```
scripts/serve.sh                         # backend + tunnel; open the printed URL on the phone
fuser -k 8100/tcp && uv run uvicorn room_valuation.server:app --host 127.0.0.1 --port 8100 &
                                         # reload code without changing the tunnel URL
```

Command line, per capture (`data/captures/<id>` or a frozen `data/fixtures/<name>`):

```
uv run room-valuation run <capture> --backend opus|astra|none        # detect and value in one go, no review
uv run room-valuation revalue <capture> --reuse frontier,refine,transcripts
                                         # replay Jev, prices and valuation on saved sources: no GPU, no Opus, about a minute
uv run room-valuation score <capture>    # against data/ground_truth/bedroom.json
uv run python scripts/merge_captures.py <capture> <capture> [--into <merged>] [--closeup CATEGORY:NAME=PATH]
                                         # several captures of one room into one
uv run python scripts/export_report.py <capture> <name>              # writes docs/results/<name>/
uv run python scripts/draw_pipeline.py   # redraws docs/design/pipeline.png
uv run python scripts/build_demo.py <capture> <name> [--run <capture>/out/runs/<time>]
                                         # demo walkthrough in demo/<name>/ (not in git: it holds the room's media)
```

Checks:

```
uv run pytest -q
uv run ruff check src scripts tests
```

Pipeline 2 runs `claude -p` (Claude Code headless) with Read, WebSearch and WebFetch. Bash,
Edit and Write are disabled.

## The app, step by step

1. **Photograph or film the room** (`/`). Photos, a video or both. For a video, sharp
   frames are taken from it: 2 a second, the blurriest third dropped, up to 16 kept. There is
   also a video-only page at `/record`. Tape dimensions are optional.
2. **Check the item list** (`/c/<id>`). Local detection shows what it found, counted by
   type. The owner removes false or duplicate items and adds anything missed.
3. **One page per item** (`/c/<id>/i/<item>`), valuable items first. Each page takes
   close-ups (labels, model stickers, spines), any number of voice notes, and a typed note.
   All of an item's notes are read together.
4. **Value the room.** The two pipelines run in parallel, then Jev, then the results
   (`/r/<id>`):
   - totals
   - every item with what each source said and which one Jev trusted
   - books by genre
   - area
   - how the sources ranked against each other

## Decisions

- **No pre-built price list.** Everything is priced live, so any room works, and Jev ranks
  three prices:
  - **Pipeline 1:** one Serper search per item from its own reading. Sources are Google
    Shopping India (Amazon.in, Flipkart, Croma, Reliance, Zepto) plus Blinkit and Zepto site
    search; the price is the median of matching listings.
  - **Pipeline 2:** its own web search.
  - **The owner:** a price paid within 2 years.

  Anything still unpriced after Jev is searched once more with Jev's chosen identity
  (`market.py`). Replayed on the saved captures, this beat running Serper only after Jev: 10.0
  against 10.6 percent error on the merged capture, 10.6 against 13.8 on the video. Every
  query is cached (`data/price_cache`).
- **RCV and ACV, as a claim uses them.**
  - RCV is the cost to buy new today. ACV is straight-line depreciation over a per-category
    useful life, down to a 10 percent salvage floor.
  - A price the owner paid counts as an RCV candidate only if the purchase was within 2
    years. The ₹450 the owner paid for the bed 35 years ago says nothing about replacing it.
- **Building fixtures** (doors, windows, switchboards) are valued but totalled separately.
  Insurers cover them under the building policy, not contents. Switchboards are valued per
  module counted: switches, sockets, regulators and plate size.
- **Jev only judges; code does the arithmetic** (this follows Jev's own docs):
  - Similarity filter: only each item's 3 most similar same-category candidates in each other
    source reach Jev.
  - Jev gives one Score per pair (different / possibly / same), with the levels spelled out,
    because Jev reads literally.
  - Merge rules applied in code:
    - Jev says "same"
    - "possibly the same" plus a mutual best match
    - one of the category in each source, unless Jev is confident they differ
    - one of the category in each source, same brand, seen in the same photo
  - Per merged item: a Choice for identity, a Choice for price (a recent owner price counts
    most), a Score for condition, and a Choice for genre.
  - Confidence under 0.5 flags the line for review.
- **Books:**
  - PP-OCR (PaddleOCR's models, run by RapidOCR because PaddlePaddle has no Python 3.14
    build) reads each photo at 0, 90 and 270 degrees and keeps the rotation where the text
    lies flat.
  - Lines are grouped into one band per spine, and the VLM reads the spines as a cross-check.
  - A title only the VLM claims must be supported by the OCR text.
  - A catalogue match needs most of the catalogue title's words in what was read.
  - Summaries and study guides are skipped.
  - A spine nobody can read becomes an "unidentified book", priced at the room's median book.
- **Owner facts are read by rules, not by the 2B model.** Prices ("16K", "1.9 lakhs",
  "Rs 2500") and ages ("3 years back", "one month old") are parsed with rules. On the first
  capture the small model invented a ₹12,000 charger and read "40 years back" as one year.
- **Apple RoomPlan: not built.** It scans only on a LiDAR iPhone or iPad. A Mac VM can
  compile it but cannot scan, and the Simulator has no LiDAR. No such device was available.
  Floor area comes from the tape if given. Otherwise it comes from the floor plan take-home
  pipeline (VGGT plus MoGe-2 on the photos or video frames), then from the frontier estimate.
- **GPT-6 Astra.** The brief asked for Astra. The OpenAI key sees `gpt-6-astra` but had no
  credits, so Pipeline 2 ran on Claude Opus 5.5. The Astra backend (`frontier.run_astra`,
  Responses API with web_search) is written but untested. Switching is one setting on the
  item list page.

## Results on the owner's bedroom

The ground truth is what the owner paid, from memory, in `data/ground_truth/bedroom.json`.
The pipeline never reads it; `score.py` uses it after the run.

Three captures of the same bedroom. Floor area for all three comes from the tape
measurement of this room: 426.7 x 365.8 cm, 168 sq ft, ceiling 312.4 cm.

| Capture | Contents RCV / ACV | Building fixtures RCV | Books | Mean RCV error, recent purchases | Report |
|---|---|---|---|---|---|
| Merged: 8 photos, a 39 s video (16 frames), 9 close-ups, 12 voice notes, typed notes | ₹3.40 / ₹2.57 lakh | ₹1.12 lakh | 11 of 11, plus 1 flagged | **10.0%** (4 items) | [report](docs/results/bedroom-merged/report.md) |
| Photos only | ₹2.69 / ₹2.14 lakh | ₹0.58 lakh | 11 of 11 | 31.0% (3 items; no table note) | [report](docs/results/bedroom-photos/report.md) |
| Video only | ₹3.30 / ₹2.51 lakh | ₹0.32 lakh | 14 (blurrier frames) | 10.6% (4 items) | [report](docs/results/bedroom-video/report.md) |

The merged capture was built with `scripts/merge_captures.py`. Detection runs once over
everything, and notes, close-ups and the owner's removals are carried over by box overlap in
the same photos. Its total is **₹4.53 lakh RCV, ₹3.11 lakh ACV**.

Against the owner's ground truth, 12 of 13 items were found. The 4 purchases within 2 years:

| Item | Owner paid | Local (Serper) | Opus | Owner note | Jev chose | Error |
|---|---|---|---|---|---|---|
| HP Victus laptop, 1 month | ₹1.9 lakh | ₹77k | ₹76k | ₹1.9 lakh | owner | 0% |
| Carrier split AC, 1 year | ₹35k | ₹32.7k | ₹35.9k | ₹35k | owner | 0% |
| L-shaped desk, 9 months | ₹8k | ₹2.9k | ₹12k | ₹8k | owner | 0% |
| Suitcase, 2 years | ₹2.5k | none | ₹3.5k | ₹2.5k | Opus | +40% |

**Honest gaps:**
- A local "wardrobe" line (₹20k) is most likely the almirah seen again. Both come from the
  local detector, so Jev cannot merge them; the review step is where it gets removed.
- Some local lines are flagged as possible double counts (₹5.5k on the merged capture) for the owner to confirm on the results page.
- Floor area from phone photos alone is weak: 125 sq ft from the video frames against 168 by
  tape. The results use the tape measurement.
- Windows and doors are Opus estimates (supply plus install), not listings.
- The router is ISP-provided (the owner said so), and the line is flagged for it.
- The Good Knight mosquito repellent was not detected by any source. The owner would add it on the item list, and pipeline 1 then prices it.

## Tuning loop

Every real capture is frozen in `data/fixtures/`. `revalue --reuse` replays one without
paying for Opus or the GPU again. Every run keeps a folder in `out/runs/<time>/` with:
- the report
- the Jev pair scores and every raw Jev call
- the settings (git commit, reuse flags)
- the score against the ground truth

Problems found this way on the real captures, and fixed:

| Found | Fix |
|---|---|
| 11 books read as 75 | one crop per photo, rotation where text lies flat, looping VLM lines split, fragments dropped |
| 19 books, near-miss catalogue records (The *Slender* Thread) | catalogue title coverage, OCR support for VLM titles, summaries skipped |
| Laptop priced at a ₹95k web median over the ₹1.9 lakh paid a month ago | Jev told that a recent owner price is the strongest evidence |
| One laptop counted twice (a misread model name) | Jev levels spelled out; same brand, same photo, one per source merges |
| ₹12k charger, "40 years" read as 1 year | rule-based price and age parsing |
| Valuation crashed on a status file race | locked atomic writes |
| Two jobs on the 8 GB GPU crashed with a CUDA error | one GPU job at a time across processes |
| A stalled Hugging Face check hung a job | models load offline |

## Layout

```
src/room_valuation/  schema, local (pipeline 1), frontier (pipeline 2), voice, ocr, books, prices,
                     jev, valuation, area, session, run, score, server
web/                 index (step 1), record (video only), items (step 2), item (step 3), results, demo
scripts/             serve.sh, fetch_weights.sh, merge_captures.py, export_report.py, build_demo.py
data/                captures/ and fixtures/ (not in git), ground_truth/, price_cache/ (not in git)
```
