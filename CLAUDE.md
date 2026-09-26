# Project instructions

Round 2 task for the Cozmo AI Applied AI / Backend Engineer role. Build an app that walks
through a room (the brief says a library; the demo is the owner's bedroom), finds every
object, reads book spines, prices everything at local Indian prices, measures the floor,
and gives an insurer the total value of the room. Two pipelines run in parallel (local
open models, and a frontier model standing in for GPT-6 Astra), the owner's voice is a third
input, and Jev (TypeSafe AI) combines and ranks all three.

## The brief (facts)

- Given by Alok Kumar (Cozmo co-founder and CEO) on a call, 2026-09-25 23:30 IST: "You've
  got two days." Deadline is about 2026-09-27 23:30 IST. Next step is a call with the other
  co-founder (Nuha Hashem, CTO).
- Full spec with timestamps: ~/dev/cozmo/meeting/task.md. Transcript:
  ~/dev/cozmo/meeting/transcript.txt (Whisper on the call recording).
- What he asked for:
  - Scan every book by its spine (title or ISBN), put it in a genre, and find its local price.
    It must work on a stack of 10 to 20 books.
  - Scan everything else too (monitors, laptops, cups, switchboards) at local prices.
  - Give the square feet, the number of shelves, the layout for multiple rooms, and the
    total value of the whole place.
  - Pipeline 1 is our own models. Pipeline 2 is "an Astra model" (GPT-6 Astra, OpenAI).
    The owner's voice is a third input. Jev combines and ranks all three.
  - Hidden monitor labels: the frontier model should get the size and resolution class from
    the image, the "closest approximate" price.
  - Switchboards (white on a white wall): he would not give the answer, research it.
  - "Apple RoomPlan in a Mac VM": not feasible, see decisions.
  - Deliverable: an app, demoed live in the room.

## Decisions (and why)

- Pipeline 2 runs Claude Opus 5.5 through `claude -p` (Claude Code headless: Read for the
  photos, WebSearch/WebFetch for prices, Bash/Edit/Write disallowed). The user chose this on
  2026-09-26. The OpenAI key sees gpt-6-astra
  but had no credits; `frontier.run_astra` (Responses API with web_search) is written but
  untested. Switching is `backend=astra` on the item list page.
- No pre-built price list. The user rejected it: it has to work in any room. Every item is
  priced live at run time:
  - Serper.dev Google Shopping with gl=in (Amazon.in, Flipkart, Croma, Reliance, Zepto show
    up as sellers).
  - A site: search on blinkit.com and zeptonow.com, because both block direct scripted
    access.
  - Serper gives 2,500 free searches; SerpAPI (250 a month) is the fallback. Every query is
    cached in data/price_cache.
  - Scraping Amazon directly was rejected (against its terms).
- RCV and ACV, as a claim uses them.
  - RCV is the cost to buy the item new today. ACV is straight-line depreciation over a
    per-category useful life, down to a 10 percent salvage floor (prices.USEFUL_LIFE).
  - A price the owner paid counts as an RCV candidate only if the purchase was 2 years ago or
    less (voice.RECENT_YEARS). Older prices stay on the line as evidence, and the age still
    drives ACV.
- Doors, windows and switchboards are building fixtures (dwelling cover, not contents).
  They are valued, but totalled separately (schema.BUILDING).
- Spines: PaddlePaddle has no Python 3.14 wheels, so RapidOCR runs PaddleOCR's PP-OCRv6
  models on ONNX Runtime.
  - The photo is read at 0, 90 and 270 degrees, the best rotation wins, and lines are
    grouped into one band per spine.
  - Qwen3-VL reads the spines too, as a cross-check.
  - Each spine goes to Open Library. A match under 0.45 is kept as the spine text, not as a
    wrong book.
- Jev, following its docs (docs.typesafe.ai; text only; no arithmetic or counting in Jev):
  - A similarity filter first: only each item's 3 most similar same-category candidates from
    each other source get scored.
  - A Score (different / possibly / same) per pair.
  - Merge rules applied in code (jev.merge):
    - score of 1.5 or more merges
    - "possibly" plus mutual best match merges
    - one item of the category in each source merges, unless Jev is confident they differ
  - Leftovers are flagged "possible double count" and totalled.
  - Per group, Choice picks the identity and the price among the candidates, Score gives
    the condition, and Choice gives the genre. Confidence under 0.5 flags the line for review.
- A voice note recorded on an item's page is linked to that item (Item.link) and skips
  pairwise matching.
- Apple RoomPlan: not built. It scans only on a LiDAR iPhone or iPad; a Mac VM can compile
  it but cannot scan, and the Simulator has no LiDAR. The floor plan take-home pipeline
  (~/dev/cozmo/floorplan-takehome) is the layout and area source instead.
- The user wanted a guided flow instead of one long narration (2026-09-26): detect first,
  review the list, then one generated page per item.

## Flow and code

```
web/index.html   step 1: room details, room photos      POST /api/captures      -> run.detect
web/items.html   step 2: item list, remove/add, backend  /c/{id}                 (session.json stage "review")
web/item.html    step 3: one page per item               /c/{id}/i/{item}        close-ups + voice note
                 "Value the room"                        POST /api/captures/{id}/submit -> run.value
web/results.html results                                 /r/{id}
```

- schema.py: the Item every source reports in; CATEGORIES, GENRES, BUILDING.
- local.py: pipeline 1.
  - detect(): OWLv2 over a general household vocabulary, then Qwen3-VL-2B identifies each
    crop; book boxes become one "books" card.
  - refine(): OCR plus the VLM on each item's close-ups; book cards split into books.
  - value(): refine, then price everything live.
- frontier.py: pipeline 2 (opus via `claude -p`, astra via the OpenAI API).
- voice.py: Whisper large-v3-turbo. run_items() reads per-item notes, extract() reads a
  room-level narration.
- ocr.py (spines, labels), books.py (Open Library), prices.py (live search, ACV),
  jev.py (filter, pair scores, merge, ranking), valuation.py (line items, totals, leaderboard),
  area.py (tape, then the floor plan pipeline, then the frontier estimate), session.py
  (session.json), run.py (detect, value, run), server.py (FastAPI, one worker thread).
- data/ground_truth/bedroom.json: what the owner paid, from memory. Only for scoring the
  output. The pipeline never reads it, and no room-specific value may appear in code,
  prompts or page tips (checked and cleaned on 2026-09-26).

## Status (2026-09-26, about 15:30 IST)

- **Real captures**, all frozen in data/fixtures (git-ignored):
  - bedroom-real: 8 photos, 7 close-ups, 12 voice notes
  - bedroom-video: 39 s video
  - bedroom-merged: both, merged with scripts/merge_captures.py, plus the AC and table
    photos and typed notes
- **Merged result:**
  - RCV Rs 4.53 lakh (contents 3.41, building fixtures 1.12), ACV Rs 3.11 lakh
  - 11 of 11 books
  - 11 of 13 ground-truth items; mean RCV error 10 percent on the 4 recent purchases
- **Tuning loop:**
  - `revalue --reuse frontier,refine,transcripts` replays a fixture for free in about a minute.
  - Every run keeps out/runs/<time>/ (report, score, settings, every raw Jev call).
  - Every Serper response is cached in data/price_cache, every Opus output in
    out/opus_raw.json.
- **The app:**
  - Photos, video or both. Per-item close-ups, several voice notes, and a typed note, all
    read together.
  - Uploads retry. One GPU job at a time across processes.
- **Open:**
  - A local-only duplicate "wardrobe"; area without tape.
  - The Astra backend is untested (no credits).
  - No whole-house roll-up.
  - The write-up for Alok.

## Running

```
cd ~/dev/cozmo/room-valuation
cp .env.example .env         # TYPESAFE_API_KEY, SERPER_API_KEY (SERPAPI_API_KEY, OPENAI_API_KEY optional)
scripts/serve.sh             # backend on 127.0.0.1:8100 + Cloudflare quick tunnel; open the printed URL on the phone
uv run room-valuation run data/captures/<id> --backend none|opus|astra   # command line, no review step
uv run pytest -q && uv run ruff check src tests
```

The quick-tunnel URL changes on every serve.sh restart. To reload code without changing
the URL, restart only uvicorn: `fuser -k 8100/tcp` and start it again. Cloudflared keeps
running.

## Environment gotchas

- RTX 5050 Laptop 8 GB (Blackwell sm_120), WSL2, Python 3.14, torch 2.14+cu130.
- TORCH_COMPILE_DISABLE=1 and TORCH_DISABLE_NATIVE_JIT=1 are set in the package
  __init__. There are no Python headers, so Triton JIT fails. They must be set before torch
  is imported.
- cuDNN SDPA is disabled (models.py). One model on the GPU at a time: OWLv2, then Qwen3-VL,
  then Whisper.
- Whisper input goes through ffmpeg (models.load_audio). The transformers pipeline cannot
  read webm from Chrome or m4a from an iPhone.
- `pkill -f <pattern>` inside a command that contains the same pattern kills its own shell.
  Kill by port instead.
- Never install xformers or flash-attn (no sm_120 wheels).

## Writing and git rules

- No em dashes anywhere. Minimal prose, bullets over paragraphs.
- Commits: one logical change each, short plain summary, no AI attribution footer (the user
  confirmed this on 2026-09-26). Identity: Chiranjeet Mishra <chiranjeetmishra13@gmail.com>,
  set in the repo config.
- Cozmo reads commit history. Commit as you work.
- Keys only in .env (git-ignored), never in code or chat logs.
