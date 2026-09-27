# Room valuation

A phone app that walks through a room and tells an insurer what it is worth:
- every object found and priced at local Indian prices
- every book read off its spine (title, author, genre, price)
- floor area, building fixtures (doors, windows, switchboards), and replacement and
  depreciated totals

There are three sources, and Jev combines them:

```
                    photos / video (any length)          close-ups, voice and typed notes per item
                          |                                          |
        detection + 3D: OWLv2 boxes, VGGT + MoGe-2 place and measure every object
                          |                                          |
          +---------------+---------------+                          |
          v                               v                          v
  Pipeline 1: local models        Pipeline 2: Claude Opus 5.5    Owner (voice + text)
  Qwen3-VL-2B names each crop     room pass: every photo, finds  Whisper transcribes,
  PP-OCRv6 reads spines, labels,  what the detector missed       rules read prices, ages
  model and serial numbers        per object: all photos of one  and configurations; the
  Open Library: title, genre      object, its dimensions and     owner's price is evidence,
  Serper: its own Indian price    price from the web             not a candidate
          |                               |                          |
          +---------------+---------------+--------------------------+
                          v
        Jev (TypeSafe): which items are the same object, which description to trust,
        every search listing judged against it (this product / similar / different),
        then which market price to trust
                          v
        valuation: exact or closest price with its range, held lines when unsure,
        ACV with per-category caps, contents vs building fixtures, books by genre
```

## After the CTO call (2026-09-26)

What the call raised, and what changed. The full list with the reasons is in
[docs/design/pipeline.md](docs/design/pipeline.md).

| Raised on the call | Now |
|---|---|
| "The owner obviously wants to maximise how much they get" | The owner's price is evidence, not a price candidate. More than 30 percent above the market asks for a receipt |
| "Items should not be depreciated to zero"; "a cap of 75 to 80 percent" | Straight-line depreciation per category with a cap, researched from US adjuster guides: electronics 80, furniture 75, building fixtures 70, books 50 |
| "Take the full photo of the laptop, you can get the RAM, all the details" | Model, product and serial numbers are read off labels (OCR, including upside down), and a computer's configuration (CPU, GPU, RAM, storage) is read and searched. A laptop with no configuration is flagged |
| The whiteboard went from ₹150 to ₹10k between runs: "how would you make sure this doesn't happen?" | Jev judges every search listing against the object: this product, a similar one, or a different one. Exact and closest prices, with a range. Unsure and 3 times apart: held for review, out of the total |
| Dedupe by 3D position (my answer) | Every detection is placed and measured in 3D; duplicates merge by position and size. A listed product whose size does not fit the 3D measurement is not the price |
| Video frames capped at 16 | Frames kept by coverage, no cap: any length of video |
| Pricing from one room-wide pass | Pipeline 2 also runs Opus once per object, with every photo of that object, for its exact identity, its dimensions from the web and its local price |
| Better models | Measured on the room's own photos (`scripts/eval_readers.py`): OCR moved to PP-OCRv6 medium (81 against 72 percent of known words). Qwen3-VL-4B (int8) was tried and scored below the 2B on crops, so the 2B stays |

## Links

| What | Where |
|---|---|
| How every stage works (with a real Jev question and answer) | [docs/design/pipeline.md](docs/design/pipeline.md) |
| Pipeline diagram | [docs/design/pipeline.png](docs/design/pipeline.png), drawn by [scripts/draw_pipeline.py](scripts/draw_pipeline.py) |
| **Result after the CTO call** (fresh detection, 3D, per-object Opus, the laptop's label) | [docs/results/bedroom-after-call/report.md](docs/results/bedroom-after-call/report.md) |
| **Demo walkthrough after the CTO call** (open in a browser) | [demo/bedroom-after-call/index.html](demo/bedroom-after-call/index.html) |
| Review of the CTO call and the improvement list | not in the repo (it quotes the call); summarised in [After the CTO call](#after-the-cto-call-2026-09-26) |
| Result, merged capture (photos + video + close-ups + notes) | [docs/results/bedroom-merged/report.md](docs/results/bedroom-merged/report.md) |
| Result, photos capture | [docs/results/bedroom-photos/report.md](docs/results/bedroom-photos/report.md) |
| Result, video capture | [docs/results/bedroom-video/report.md](docs/results/bedroom-video/report.md) |
| Result, merged inputs re-run from scratch (no cached model, Jev or search answers) | [docs/results/bedroom-fresh/report.md](docs/results/bedroom-fresh/report.md) |
| Owner's ground truth (used only for scoring) | [data/ground_truth/bedroom.json](data/ground_truth/bedroom.json) |
| Project notes (brief, decisions, status) | [CLAUDE.md](CLAUDE.md) |
| Skills used in development (ponytail, MIT) | [.claude/skills/](.claude/skills/README.md) |

Each result folder has a readable `report.md`, plus `report.json`, `score.json` and
`floor_plan.png`.

## Demo walkthroughs

Each demo is one real capture, step by step, with the owner's own photos, video and voice notes:
capture, detection boxes, the 3D placement, the owner's list, close-ups and voice notes with
their transcripts, what each pipeline read, Jev's questions and answers (including its verdict on
every listing), the valuation and the score against the ground truth.

| Demo | What it is |
|---|---|
| [demo/bedroom-after-call/](demo/bedroom-after-call/index.html) | **Latest.** The merged bedroom re-detected and re-valued after the CTO call: 3D, listing verdicts, per-object Opus, the laptop's label, owner price as evidence, capped depreciation |
| [demo/bedroom-fresh/](demo/bedroom-fresh/index.html) | Before the call: the same inputs re-run from scratch with no caches |
| [demo/bedroom/](demo/bedroom/index.html) | Before the call: the merged capture as shown on the call |
| [demo/index.html](demo/index.html) | The list of demos |

**To open one:** clone the repo and open `demo/<name>/index.html` in a browser. It is static (no
server): `index.html`, `demo.js`, `app.css`, `data.js` (every number, Jev call and transcript of
that run) and `media/` (photos, crops, video, voice notes). Arrow keys move between the steps.
With the app running (`scripts/serve.sh`), the same demos are at http://127.0.0.1:8100/demo/, and
the "Open the live review page" link works too.

**To build one** from any valued capture:

```
uv run python scripts/build_demo.py data/captures/<id> <name> --run data/captures/<id>/out/runs/<time> --title "<text>"
```

The results behind each demo are also exported as readable reports in
[docs/results/](docs/results/): `report.md`, `report.json`, `score.json`, `floor_plan.png`.

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
| Every valued capture | `/r/` | Each capture with results, newest first: its label (`label` in its meta.json), what it holds, RCV and ACV, and a link to its results page |
| Results and final review | `/r/<capture id>` ([web/results.html](web/results.html)) | Totals, every item with every source's price and Jev's choice, books by genre, floor area and plan. **Remove**, **Same as** and **Undo** per line |
| Demo walkthroughs | `/demo/` lists them, `/demo/<name>/` ([web/demo.html](web/demo.html)) | One real capture step by step: photos, video, detection boxes, the owner's list, close-ups and voice notes with transcripts, what each pipeline read, Jev's questions and answers, the valuation, the score. Built by `scripts/build_demo.py` |

The API behind the pages is in [src/room_valuation/server.py](src/room_valuation/server.py): `POST /api/captures`,
`/api/captures/<id>/session`, `/items/<item>`, `/items`, `/detect`, `/submit`, `/status`, `/report`, `/review`.

## Commands

Setup, once:

```
uv sync                                  # Python 3.14, torch 2.14 (CUDA 13)
cp .env.example .env                     # TYPESAFE_API_KEY, SERPER_API_KEY; OPENAI_API_KEY only for --backend astra
scripts/fetch_weights.sh                 # OWLv2, Qwen3-VL-2B, Whisper large-v3-turbo into the Hugging Face cache
                                         # 3D needs ~/dev/cozmo/floorplan-takehome (VGGT-1B, MoGe-2) next to this repo
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
uv run room-valuation revalue <capture> --reuse frontier,object,refine,transcripts
                                         # replay Jev, prices and valuation on saved sources: no GPU, no Opus, a few minutes
PRICE_CACHE=<capture>/out/price_cache uv run room-valuation revalue <capture> --reuse ""
                                         # everything afresh: local models, Whisper, Opus, Jev, and Serper with an empty cache
uv run room-valuation score <capture>    # against data/ground_truth/bedroom.json
uv run python scripts/merge_captures.py <capture> <capture> [--into <merged>] [--closeup CATEGORY:NAME=PATH] [--unreviewed remove]
                                         # several captures of one room into one, or one capture re-detected afresh;
                                         # the owner's review is carried by photo content and 3D position
uv run python scripts/eval_readers.py ocr|vlm <capture> [--model <hf id>] [--int8]
                                         # score OCR tiers and VLMs on the room's own photos
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

1. **Photograph or film the room** (`/`). Photos, a video or both. For a video, frames are
   kept by coverage: 2 a second, motion blur dropped, and a frame each time the view moves on,
   with no cap. There is also a video-only page at `/record`. Tape dimensions are optional.
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
  - **The owner:** a price paid within 2 years, as evidence only since the CTO call (checked
    against the market; far above it asks for a receipt).

  Anything still unpriced after Jev is searched once more with Jev's chosen identity
  (`market.py`). Replayed on the saved captures (with the earlier Opus pass), this beat running
  Serper only after Jev: 10.0 against 10.6 percent error on the merged capture, 10.6 against
  13.8 on the video. Every
  query is cached (`data/price_cache`).
- **RCV and ACV, as a claim uses them.**
  - RCV is the cost to buy new today. ACV is straight-line depreciation over a per-category
    useful life, adjusted for condition and capped per category (80 percent electronics, 75
    furniture, 70 building fixtures, 50 books; before the CTO call, a 10 percent floor).
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
  - Per merged item: a Choice for identity, a Score for condition, a Choice for genre; then a
    Score for every search listing against that identity (this product, similar, different);
    then a Choice for price among the market candidates.
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

### After the CTO call (capture 20260927-061610-8b4353, run 20260927-091101)

The merged bedroom rebuilt from its raw photos and video: a fresh detection over 8 photos and
30 frames (kept by coverage), every box placed in 3D, the owner's review carried over by photo
content and 3D position, and the owner's two photos of the laptop's underside label added as
close-ups. The Opus room pass ran from scratch with an empty Serper cache ($3.80), then Opus
once per object ($11.66). The owner's prices are evidence only.

| | Result |
|---|---|
| RCV / ACV | **₹3.30 lakh / ₹2.39 lakh** (contents ₹2.52 / ₹2.04 lakh, building fixtures ₹0.79 / ₹0.36 lakh) |
| Held for review, not in the total | 3 lines, ₹630 to ₹21,049: the "wardrobe" (a blurred curtain), a stool and a bedsheet where Jev was unsure and the prices 4 to 6 times apart |
| Items | 52 lines; 13 of 13 ground-truth items; 11 of 11 books, plus 1 flagged fragment |
| **Mean RCV error, 4 recent purchases** | **15.6%**, with no owner price used |
| Jev | 107 pairs scored, 286 skipped; 499 questions in 14 calls, about 10 s; 256 listings judged (39 this product, 103 similar, 114 different) |

| Item | Owner paid | Local (Serper) | Opus, room | Opus, per object | Chosen | Error |
|---|---|---|---|---|---|---|
| HP Victus laptop, 1 month | ₹1.9 lakh | ₹85k (exact model) | ₹74k | ₹1.32 lakh (15-fb3185AX, read off the label) | per object | -30.5% |
| Carrier split AC, 1 year | ₹35k | ₹32.5k | ₹35.9k | ₹35.5k | per object | +1.4% |
| L-shaped desk, 9 months | ₹8k | none | ₹9k | ₹9k | per object | +12.5% |
| Suitcase, 2 years | ₹2.5k | none | ₹3.8k | ₹2k | per object | -18.0% |

- **The laptop.** Before, every source priced the base HP Victus 15 (₹74k to ₹79k) and the
  15 percent came from trusting the owner's ₹1.9 lakh. Now the model number is read off the
  label, its configuration (Ryzen 7 260, RTX 5050, 24 GB, 1 TB) comes from the official
  specification, and it is priced new at ₹1,31,999 (Vijay Sales; MRP ₹2,01,865). The owner's
  ₹1.9 lakh is 44 percent above that, so the line asks for a receipt.
- **Each source alone** on those four: Opus per object 15.6 percent, the Opus room pass 32
  percent.
- **Depreciation** is capped per category: the 40-year-old almirah keeps 25 percent of its
  replacement cost, not 10.

Three captures of the same bedroom. Floor area for all three comes from the tape
measurement of this room: 426.7 x 365.8 cm, 168 sq ft, ceiling 312.4 cm.

| Capture | Contents RCV / ACV | Building fixtures RCV | Books | Mean RCV error, recent purchases | Report |
|---|---|---|---|---|---|
| Merged: 8 photos, a 39 s video (16 frames), 10 close-ups, 12 voice notes, typed notes | ₹3.16 / ₹2.49 lakh | ₹0.74 lakh | 11 of 11, plus 1 flagged | **15.0%** (4 items) | [report](docs/results/bedroom-merged/report.md) |
| Photos only | ₹2.69 / ₹2.14 lakh | ₹0.58 lakh | 11 of 11 | 31.0% (3 items; no table note) | [report](docs/results/bedroom-photos/report.md) |
| Video only | ₹3.30 / ₹2.51 lakh | ₹0.32 lakh | 14 (blurrier frames) | 10.6% (4 items) | [report](docs/results/bedroom-video/report.md) |
| Merged inputs, re-run from scratch: fresh detection, OCR, Whisper, Opus, Jev and Serper (empty cache) | ₹3.37 / ₹2.58 lakh | ₹0.85 lakh | 11 of 11, plus 1 flagged | 17.6% (4 items) | [report](docs/results/bedroom-fresh/report.md) |

The merged capture was built with `scripts/merge_captures.py`. Detection runs once over
everything, and notes, close-ups and the owner's removals are carried over by box overlap in
the same photos. Its total is **₹3.90 lakh RCV, ₹2.82 lakh ACV**. It is the latest full run:
every photo and all 10 close-ups through Opus, then Jev and Serper.

Against the owner's ground truth, all 13 items were found. The 4 purchases within 2 years:

| Item | Owner paid | Local (Serper) | Opus | Owner note | Jev chose | Error |
|---|---|---|---|---|---|---|
| HP Victus laptop, 1 month | ₹1.9 lakh | ₹77k | ₹79k | ₹1.9 lakh | owner | 0% |
| Carrier split AC, 1 year | ₹35k | ₹32.7k | ₹35.9k | ₹35k | owner | 0% |
| L-shaped desk, 9 months | ₹8k | ₹2.9k | ₹8k | ₹8k | owner | 0% |
| Suitcase, 2 years | ₹2.5k | none | ₹4k | ₹2.5k | Opus | +60% |

**Run to run.** Three full runs on the same merged inputs came to ₹4.53, ₹3.90 and ₹4.22 lakh
RCV. The owner's list, the books and the recent purchases the owner priced stay put. What
moves is what a model estimates: doors and windows (₹1.12, ₹0.74, ₹0.85 lakh), old furniture,
and borderline Jev price choices such as the whiteboard sheet (the owner's ₹150 or a ₹8k to
₹10.6k listing for a real whiteboard).

**Honest gaps** (the numbers below are the run before the CTO call, unless marked):
- A local "wardrobe" line (₹20k) is most likely the almirah seen again. Both come from the
  local detector, so Jev cannot merge them; the review step is where it gets removed. After
  the call: it was a blurred frame of the curtain, and it is held out of the total.
- After the call: 3D sizes hold for rigid things seen whole (the laptop), not for soft or
  sprawling ones (a bedsheet, a charger with its cable), so they are used only for furniture,
  appliances and electronics.
- After the call: the depreciation caps are a researched default, to be replaced by a
  carrier's own table.
- Some local lines are flagged as possible double counts (₹4.1k on the merged capture) for the owner to confirm on the results page.
- Floor area from phone photos alone is weak: 125 sq ft from the video frames against 168 by
  tape. The results use the tape measurement.
- Windows and doors are Opus estimates (supply plus install), not listings, and they move run to
  run: two Opus passes on the same photos put building fixtures at ₹1.12 and ₹0.74 lakh.
- The router is ISP-provided (the owner said so), and the line is flagged for it.
- The Good Knight mosquito repellent was not detected by any source. The owner added it on the
  item list with a close-up; pipeline 1 read it and priced it at ₹160 (median of 16 listings).

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
src/room_valuation/  schema, local (pipeline 1), frontier (pipeline 2: room pass and per object), voice, ocr,
                     books, prices, specs (configurations and label numbers), geometry (3D), jev, valuation,
                     area, session, run, score, server
web/                 index (step 1), record (video only), items (step 2), item (step 3), results, demo
scripts/             serve.sh, fetch_weights.sh, merge_captures.py, export_report.py, build_demo.py,
                     geometry_worker.py (VGGT + MoGe-2), eval_readers.py (model choice), draw_pipeline.py
demo/                the demo walkthroughs, with the room's photos, video and voice notes
docs/                design/pipeline.md and pipeline.png; results/<capture>/ reports
data/                captures/ and fixtures/ (not in git), ground_truth/, price_cache/ (not in git)
```
