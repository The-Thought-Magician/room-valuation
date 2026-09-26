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

How each stage works, with a real Jev question and answer: [docs/design/pipeline.md](docs/design/pipeline.md).
Results per capture: [docs/results/](docs/results/) (photos, video, merged).

## Run it

```
uv sync
cp .env.example .env        # TYPESAFE_API_KEY, SERPER_API_KEY; OPENAI_API_KEY only for Astra
scripts/fetch_weights.sh    # once: OWLv2, Qwen3-VL-2B, Whisper large-v3-turbo
scripts/serve.sh            # backend on 127.0.0.1:8100 + Cloudflare tunnel; open the printed URL on the phone
```

Pipeline 2 runs `claude -p` (Claude Code headless) with Read, WebSearch and WebFetch.
Bash, Edit and Write are disabled. It needs a logged-in Claude Code on the machine.

Command line:

```
uv run room-valuation run data/captures/<id> --backend opus|astra|none     # detect and value, no review
uv run room-valuation revalue data/captures/<id> --reuse frontier,refine,transcripts   # replay, free
uv run room-valuation score data/captures/<id>                             # against data/ground_truth
uv run python scripts/merge_captures.py <capture> <capture> [--closeup CATEGORY:NAME=PATH]
uv run pytest -q
```

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

**The capture.** The final capture (`data/fixtures/bedroom-merged-2026-09-26`) merges:
- a photos capture: 8 room photos, 7 close-ups, 12 voice notes
- a 39 s video capture: 16 sharp frames
- two more close-ups (AC, table) and typed notes

It was merged with `scripts/merge_captures.py`. Detection runs once over everything. Notes,
close-ups and the owner's removals are carried over by box overlap in the same photos.

| | Replacement (RCV) | After depreciation (ACV) |
|---|---|---|
| Contents (incl. 11 books, ₹5.7k) | ₹3.41 lakh | ₹2.57 lakh |
| Building fixtures (2 windows, 3 doors, switchboards, MCB) | ₹1.12 lakh | ₹0.54 lakh |
| **Total** | **₹4.53 lakh** | **₹3.11 lakh** |

**Against the ground truth:**
- 11 of 13 items found. Mean RCV error 10.0 percent on the 4 items with a purchase within 2
  years: laptop 0, table 0, AC 0, suitcase +40.
- 11 of 11 books read with title, author, genre and price, plus one flagged "unidentified
  book".

| Item | Owner paid | Local | Opus | Owner note | Jev chose |
|---|---|---|---|---|---|
| HP Victus laptop, 1 month | ₹1.9 lakh | ₹77k (web median) | ₹76k | ₹1.9 lakh | owner |
| Carrier split AC, 1 year | ₹35k | ₹32.9k | ₹35.9k | ₹35k | owner |
| L-shaped desk, 9 months | ₹8k | ₹2.9k | ₹12k | ₹8k | owner |
| Suitcase, 2 years | ₹2.5k | none | ₹3.5k | ₹2.5k | Opus |
| Acer 24 inch monitor, 3 years | ₹16k | ₹12.2k | ₹13k | too old to count | local |

**Honest gaps:**
- A local "wardrobe" line (₹20k) is most likely the almirah seen again. Both come from the
  local detector, so Jev cannot merge them; the review step is where it gets removed.
- Two local curtain lines are flagged as possible double counts (₹22.5k flagged in total).
- The floor came out at 125 sq ft from the video frames, against 168 sq ft by tape. No tape
  dimensions were entered; with them the area is exact.
- Windows and doors are Opus estimates (supply plus install), not listings.
- The router is ISP-provided (the owner said so), and the line is flagged for it.
- The whiteboard and the Good Knight refill were not matched.

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
web/                 index (step 1), record (video only), items (step 2), item (step 3), results
scripts/             serve.sh, fetch_weights.sh, merge_captures.py
data/                captures/ and fixtures/ (not in git), ground_truth/, price_cache/ (not in git)
```
