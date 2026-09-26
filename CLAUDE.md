# Project instructions

Round 2 task for the Cozmo AI Applied AI / Backend Engineer role. Build an app that walks
through a room (the brief says a library; the demo is the owner's bedroom), finds every
object, reads book spines, prices everything at local Indian prices, measures the floor,
and gives an insurer the total value of the room. Two pipelines run in parallel (local
open models, and a frontier model standing in for GPT-6 Astra), the owner's voice and typed
notes are a third input, and Jev (TypeSafe AI) combines and ranks all three.

How it works in detail: docs/design/pipeline.md (diagram docs/design/pipeline.png, drawn by
scripts/draw_pipeline.py). Results per capture: docs/results/.

## The brief (facts)

- Given by Alok Kumar (Cozmo co-founder and CEO) on a call, 2026-09-25 23:30 IST: "You've
  got two days, have a stab at this, get back to me." Deadline is about 2026-09-27
  23:30 IST. Next step is a call with the other co-founder (Nuha Hashem, CTO), then a
  decision about two days later.
- Full spec with timestamps: ~/dev/cozmo/meeting/task.md. Transcript:
  ~/dev/cozmo/meeting/transcript.txt (Whisper on the call recording). The recording is
  ~/dev/cozmo/meeting/audio.mp3.
- **Deliverable, in his words (32:13):** "an app where you can show me how you built this, as
  it's working in a library. It could be even in your room." That means a live demo plus
  showing how it was built. **He did not ask for a written report**; README, the design doc
  and docs/results cover "how it was built".
- What the app must do:
  - Scan every book by its spine (title or ISBN), put it in a genre, and find its local price.
    It must work on a stack of 10 to 20 books.
  - Scan everything else too (monitors, laptops, cups, switchboards) at local prices.
  - Give the square feet, the number of shelves, the layout for multiple rooms, and the
    total value of the place.
  - Pipeline 1 is our own models. Pipeline 2 is "an Astra model" (GPT-6 Astra, OpenAI).
    The owner's voice is a third input. Jev combines and ranks all three.
  - Hidden monitor labels: the frontier model should get the size and resolution class, the
    "closest approximate" price.
  - Switchboards (white on a white wall): he would not give the answer, research it.
    Answered: modules counted per board, valued as building fixtures.
  - "Apple RoomPlan in a Mac VM": not feasible, see decisions.
- Serper runs on its free tier (2,500 searches).
- Questions he asked on the call worth preparing for the co-founder call: VAD, WER and
  voice-agent evals,
  and what happens when an engineer trusts a wrong agent answer.

## Decisions (and why)

- **Pipeline 2 is Claude Opus 5.5 through `claude -p`** (Claude Code headless: Read for the
  photos, WebSearch/WebFetch for prices, Bash/Edit/Write disallowed). The user chose this on
  2026-09-26. The OpenAI key sees gpt-6-astra
  but had no credits; `frontier.run_astra` (Responses API with web_search) is written but
  untested. Switching is `backend=astra` on the item list page.
- **No pre-built price list.** The user rejected it: it has to work in any room. Every item is
  priced live at run time:
  - Serper.dev Google Shopping with gl=in (Amazon.in, Flipkart, Croma, Reliance and Zepto
    appear as sellers).
  - A site: search on blinkit.com and zeptonow.com, because both block direct scripted
    access.
  - Serper gives 2,500 free searches; SerpAPI is the fallback. Every query is cached in
    data/price_cache.
  - Scraping Amazon directly was rejected (against its terms).
- **RCV and ACV, as a claim uses them.**
  - ACV is straight-line over a per-category useful life, down to a 10 percent salvage floor.
  - A price the owner paid counts as an RCV candidate only if the purchase was within 2
    years (voice.RECENT_YEARS).
- **Owner facts are read by rules, not by the 2B model**: prices and ages via
  voice.parse_price and parse_age; "free" or "provided" is flagged. Qwen only reads the
  brand.
- **Building fixtures** (doors, windows, switchboards, the MCB box) are valued but totalled
  apart from contents (schema.BUILDING).
- **Books:**
  - RapidOCR runs PaddleOCR's PP-OCRv6 (PaddlePaddle has no Python 3.14 wheels). It reads at
    0, 90 and 270 degrees and keeps the flat-text rotation, with one band per spine.
  - A VLM-only title needs half its words supported by the OCR.
  - An Open Library match needs half string similarity plus half title coverage, at least
    0.6. Summaries and study guides are skipped.
  - A partial read of a known book is dropped. Leftovers become "unidentified book" at the
    room's median book price.
- **Jev** (docs.typesafe.ai; text only; no arithmetic in Jev):
  - Links first:
    - an owner note belongs to its item
    - a frontier item that lists an item's close-up (same category, shared word) is that
      item
  - Similarity filter: only comparable categories (jev.COMPATIBLE: bedding and furniture,
    appliance and electrical fixture, and so on; building fixtures never cross), and the top
    3 per other source.
  - One Score per pair, with spelled-out levels. Books have their own levels.
  - Merge rules in code (jev._merge_scored):
    - Jev says same
    - "possibly" plus mutual best match
    - one of the category per source, unless Jev is confident they differ
    - one of the category per source, same brand, in the same photo
  - Per group: Choice for identity, Choice for price (a recent owner price counts most),
    Score for condition, Choice for genre.
  - Every call is logged.
- **Area**, in order: tape, then a floor plan the take-home already measured, then the floor
  plan pipeline on these photos, then the frontier estimate. Every candidate is shown. The
  bedroom captures use the take-home's tape (426.7 x 365.8 cm, ceiling 312.4) and its ARCore
  plan (15.68 m²) via meta.json `length_cm`/`width_cm`/`tape_source`/`floorplan_plan`
  (user's instruction, 2026-09-26: same room).
- **Apple RoomPlan: not built.** It scans only on a LiDAR iPhone or iPad; a Mac VM can compile
  it but cannot scan, and the Simulator has no LiDAR.
- **UX, by the user's direction (2026-09-26):**
  - Detect first, owner reviews the list, then one generated page per item.
  - Photos, video or both.
  - Several voice notes plus a typed note per item, read together.
  - A final review on the results page (Remove / Same as / Undo), stored in session.json
    `line_review` by a stable line key and applied on every replay.

## Flow and code

```
web/index.html   step 1: room details, photos and/or video   POST /api/captures          -> run.detect
web/record.html  step 1, video only                           /record
web/items.html   step 2: item list, remove/add, backend       /c/{id}                     session.json stage "review"
web/item.html    step 3: one page per item                    /c/{id}/i/{item}            close-ups, voice notes, typed note
                 "Value the room"                             POST /api/captures/{id}/submit -> run.value
web/results.html results and the owner's final review         /r/{id}                     POST /api/captures/{id}/review
```

- **schema.py:** the Item every source reports in; CATEGORIES, GENRES, BUILDING.
- **local.py** (pipeline 1):
  - detect(): OWLv2 plus Qwen3-VL-2B.
  - refine(): OCR and the VLM on close-ups; spines.
  - value(): refine, then live prices.
- **frontier.py:** pipeline 2 (opus via `claude -p`, astra via the OpenAI API).
- **voice.py:** Whisper plus rule parsing; run_items() reads each item's voice notes and typed
  note as one statement.
- **Supporting modules:**
  - ocr.py, books.py, prices.py
  - jev.py (links, filter, pair scores, merge, ranking, call log)
  - valuation.py (line items, totals, leaderboard, reviewed_report)
  - area.py, session.py
  - run.py (detect, value, per-run folders, GPU lock use)
  - score.py (against the ground truth)
  - server.py (FastAPI, one worker thread)
- **Scripts:**
  - serve.sh, fetch_weights.sh
  - merge_captures.py (several captures into one, carrying media, notes and review
    decisions)
  - export_report.py (docs/results/<name>/)
  - draw_pipeline.py
- **data/ground_truth/bedroom.json:** what the owner paid, from memory, including voice-note
  corrections (monitor 24 inch, Rs 16k, 3 years; stool 8 years; table Rs 8k, 9 months).
  - Only for scoring. The pipeline never reads it.
  - No room-specific value may appear in code, prompts or page tips (cleaned on
    2026-09-26).
  - Values that repeat a prompt example are dropped (local.EXAMPLE_VALUES).

## Status (2026-09-26, about 16:30 IST)

- **Real captures**, frozen in data/fixtures (git-ignored):
  - bedroom-real: 8 photos, 7 close-ups, 12 voice notes
  - bedroom-video: 39 s video
  - bedroom-merged: both, plus the AC and table photos and typed notes
- **Live captures** in data/captures:
  - 072711 (photos), 080711 (video), 090044 (merged)
  - The merged one's review page is /r/20260926-090044-d552ae.
- **Merged result:**
  - RCV Rs 4.53 lakh (contents 3.41, building fixtures 1.12), ACV Rs 3.11 lakh
  - Area 168 sq ft from tape
  - 11 of 11 books plus one flagged unidentified
  - 11 of 13 ground-truth items; mean RCV error 10 percent on the 4 recent purchases
    (laptop, table and AC at 0, suitcase +40)
- **Exported** to docs/results/bedroom-{photos,video,merged}: report.md, report.json,
  score.json, floor_plan.png.
- **Tuning loop:** `revalue --reuse frontier,refine,transcripts` replays a fixture for free in
  about a minute. Every run keeps out/runs/<time>/ (report, score, settings, every raw Jev
  call).
- **Open:**
  - The "wardrobe" line on the merged capture is most likely the almirah again. The owner
    should mark it "Same as" the almirah on the results page (not done yet).
  - The Astra backend is untested (no credits).
  - No whole-house roll-up: one capture is one room.
  - Demo preparation for Alok: the order to show things, and a fresh live capture on the
    day. No write-up is needed.

## Running

```
cd ~/dev/cozmo/room-valuation
cp .env.example .env         # TYPESAFE_API_KEY, SERPER_API_KEY (SERPAPI_API_KEY, OPENAI_API_KEY optional)
scripts/serve.sh             # backend on 127.0.0.1:8100 + Cloudflare quick tunnel; open the printed URL on the phone
uv run room-valuation run data/captures/<id> --backend none|opus|astra
uv run room-valuation revalue data/fixtures/<name> --reuse frontier,refine,transcripts
uv run room-valuation score data/captures/<id>
uv run python scripts/merge_captures.py <capture> <capture> [--into <merged>] [--closeup CAT:NAME=PATH]
uv run python scripts/export_report.py <capture> <name>
uv run pytest -q && uv run ruff check src scripts tests
```

The quick-tunnel URL changes on every serve.sh restart; the current one is
https://wool-segment-dip-endif.trycloudflare.com. To reload code without changing the URL,
restart only uvicorn: `fuser -k 8100/tcp` and start it again. Cloudflared keeps running.

**Restart uvicorn after code changes.** The server keeps the code it started with. A
restart while a valuation runs kills it and orphans its `claude -p`: find it with
`ps -eo pid,ppid,etimes,args` and kill it.

## Environment gotchas

- RTX 5050 Laptop 8 GB (Blackwell sm_120), WSL2, Python 3.14, torch 2.14+cu130.
- TORCH_COMPILE_DISABLE=1, TORCH_DISABLE_NATIVE_JIT=1 and HF_HUB_OFFLINE=1 are set in the
  package __init__:
  - no Python headers, so Triton JIT fails
  - a stalled Hub check once hung a job
  - scripts/fetch_weights.sh downloads with offline off
- One GPU job at a time across processes (models.gpu_lock, a file lock). Two jobs on the
  card crashed one with a CUDA illegal memory access, and a CUDA error poisons that process
  until restart.
- Whisper input goes through ffmpeg (models.load_audio). The transformers pipeline cannot
  read webm or m4a.
- `pkill -f` or `pgrep -f` with a pattern that appears in the same command line matches its
  own shell. This happened three times on 2026-09-26. Kill by port or by PID.
- Never install xformers or flash-attn (no sm_120 wheels).

## Writing and git rules

- No em dashes anywhere. Minimal prose, bullets over paragraphs.
- Commits: one logical change each, short plain summary, no AI attribution footer (the user
  confirmed this on 2026-09-26). Identity: Chiranjeet Mishra <chiranjeetmishra13@gmail.com>,
  set in the repo config.
- Cozmo reads commit history. Commit as you work.
- Keys only in .env (git-ignored), never in code or chat logs.
- Photos, video and voice notes of the owner's room stay out of git (data/captures,
  data/fixtures). Only exported reports go in docs/results.
