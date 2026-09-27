# How the pipeline works

![pipeline](pipeline.png)

The diagram is drawn by `scripts/draw_pipeline.py`; rerun it after changing the pipeline.
Numbers below are from the merged bedroom capture (`docs/results/bedroom-merged`).

## 1. Capture (phone, `web/index.html`, `web/record.html`)

- The owner gives photos, a video, or both, plus room details: room name, city, and tape
  dimensions if known.
- Photos are EXIF-upright and at most 2048 px.
- A video goes through `run.video_frames`, chosen by coverage, not by count, so a video of any
  length works:
  1. ffmpeg takes 2 frames a second.
  2. Motion blur is dropped: variance of the Laplacian under 0.8 of the median.
  3. A frame is kept each time under 8 percent of its ORB features match the last kept frame,
     that is, when the camera has moved on to something new. There is no cap: a longer walk
     through more room keeps more frames, a slow pan over one wall keeps few.
  4. They are used exactly like photos.
- The bedroom's 39 s walk-through gives 79 frames at 2 a second; 30 are kept (it was a fixed 16
  before the CTO call). Neighbouring frames half a second apart match only 15 to 25 percent of
  their features on this fast, close walk-through, hence the low threshold.
- The capture is stored under `data/captures/<id>/`: `meta.json`, `photos/room/`, `video.*`,
  `session.json`.

## 2. Detection and the owner's list (`local.detect`, `web/items.html`)

1. **OWLv2** (`google/owlv2-base-patch16-ensemble`) runs over each photo with a general
   household vocabulary of about 60 prompts. Nothing is tuned to one room.
2. Boxes go through NMS, tiny boxes are dropped, and at most 14 are kept per photo.
3. **Qwen3-VL-2B** looks at each crop and returns category, name, readable brand/model,
   size, printed text and condition. Answers that repeat the prompt's example are dropped
   (see section 9).
4. **Every box is placed in 3D** (`geometry.py`, run between the two models so VGGT has the GPU):
   - `scripts/geometry_worker.py` runs in the floor plan take-home's environment. VGGT-1B gives
     a 3D point for every pixel and a camera for every photo and frame, in one world.
   - Any number of images: VGGT runs in chunks of 24 that share 6 images, and each chunk is
     aligned to the first by a similarity transform (Umeyama) on the pixels of the shared
     images. 24 images peaked at 5.2 GB on the 8 GB card.
   - MoGe-2 monocular metric depth gives the scale, and the cameras' up axes level the world.
   - A box becomes the points of the object's front surface (the nearest depth band inside the
     box, shrunk off the background). Their median is the position; their spread across and up
     is the width and height. Each view is measured on its own and the median taken.
   - Checked on the bedroom: the 15.6 inch laptop measured 37 cm wide (it is 36), the 24 inch
     monitor 40 cm (it is 53). Sizes only rule out a product at nearly double or half the size.
5. The same object in several photos becomes one item:
   - **3D first:** two boxes within a quarter metre (or 40 percent of the object's larger
     side), of a similar size (within 2.5 times), are one object whatever each view called it.
     Two same-named objects a metre or more apart stay two. A pillow on the bed is one place
     but not one size, so it stays a pillow.
   - otherwise: box containment above 0.45 within one photo; same brand or similar names
     across photos
6. Book boxes become one "books" card. Its spines are read in step 4, not from the crop.
7. The owner sees the list with counts per type, removes false or duplicate items, and adds
   anything missed. This is stored in `session.json`.

## 3. One page per item (`web/item.html`)

Items are walked through most valuable first (laptop, monitor, appliance, furniture, books,
and so on). Each page takes:
- **close-ups:** a model sticker, a rating plate, spines, the screen showing its resolution
- **any number of voice notes** (`items/<id>/voice_NN.*`)
- **a typed note**

All notes on an item are read together as one owner statement. Uploads retry if the server
is briefly unavailable.

## 4. Three sources, in parallel (`run.value`)

The frontier model is remote and runs in its own thread. The GPU work (local models,
Whisper) runs under a file lock, one job at a time across processes: two jobs on the 8 GB
card once crashed one of them.

### Pipeline 1: local models (`local.refine`, `local.price_all`)

- **Close-ups:**
  - PP-OCR reads every line of text on the label. These are PaddleOCR's PP-OCRv6 models (the
    medium tier) run through RapidOCR on ONNX Runtime, because PaddlePaddle has no Python 3.14
    build. Labels are read at 0, 90, 180 and 270 degrees: the etched label under a laptop,
    photographed from the front, is upside down. Electronics are also read in enlarged
    overlapping tiles, for small print.
  - Qwen3-VL reads brand, model, size and specs, given the OCR text as a hint.
  - **Model, product and serial numbers are read by rules on the OCR text** (`specs.label_ids`),
    not by the VLM: on the laptop's labels the 2B put "Victus by HP Gaming Laptop" in the model
    field, and took the radio module for the model and the regulatory number for the serial.
    The rules take the code after the product name or "Model", the ProdID or P/N line and the SN#
    line, and skip radio, regulatory (RMN, TPN), BIS, standards, power and warranty lines.
  - **The configuration** (`specs.parse`): CPU, GPU, RAM, storage, screen, refresh and
    resolution, by rules, from the OCR, the frontier model's reading or the owner's words. A
    computer with no configuration is flagged: priced as the base model, with the photo that
    would fix it (the label underneath, the box, Settings > About).
  - The models were chosen on the room's own photos (`scripts/eval_readers.py`, expected words in
    `data/ground_truth/readers_bedroom.json`): PP-OCRv6 medium read 81 percent of the known words
    against 72 for small. Qwen3-VL-4B (int8 through torchao; its bf16 does not fit 8 GB and
    bitsandbytes has no Blackwell kernels) scored 0.70 on crops against the 2B's 0.85, 0.56 on
    close-ups against 0.50, the same on spines, in twice the time. The 2B stays.
- **Books** (`local._read_spines`):
  - One full-resolution crop per photo around all book boxes, or the spine close-ups.
  - PP-OCR reads at 0, 90 and 270 degrees. The rotation where the text lies flat wins, and
    lines are grouped into one band per spine.
  - Qwen reads the spines too. A title that only Qwen claims must have half its words
    supported by the OCR text; this stopped "Anne of Green Gables" appearing.
  - Each spine text goes to Open Library. A match is accepted only if half string similarity
    plus half title coverage reaches 0.6; this stopped "The *Slender* Thread". Summaries and
    study guides are skipped.
  - Unmatched text that shares a word with a matched book is a partial read and is dropped.
    What is left becomes an "unidentified book", priced at the room's median book.
- **Prices: pipeline 1 gives its own value for every item**, as the brief asks ("get the
  local price of the books… categorize… by their value. This is one pipeline"). That way Jev
  has two independent market values to rank, plus the owner's.
  - One Serper search per item, from this pipeline's own reading (`prices.query_for`):
    - repeated words are dropped ("Acer" plus "Acer 24 inch monitor" says Acer once)
    - vague one-word names get a category word ("switch" becomes "switch electrical wall",
      after "switch" matched Nintendo Switch listings)
    - books search "title author paperback"
    - a model number read off a close-up's label is searched as that exact model first, then its
      product number, and only listings naming it count (`prices.lookup`). The configuration those
      listings state fills the item's spec when none was read
    - a computer's search carries its configuration (`specs.search_words`: "HP laptop Ryzen 7
      260 RTX 5050"), and a listing must name its GPU
    - used, refurbished and open-box listings are dropped: a replacement cost is the price new
  - Sources:
    - Serper Google Shopping for India (Amazon.in, Flipkart, Croma, Reliance, Zepto appear
      as sellers)
    - a Google site search of blinkit.com and zeptonow.com for small goods
  - Only listings whose titles share at least half the query words, and the brand, count.
    The median of those is this pipeline's own price, with the 25th to 75th percentile as its
    range. The best 10 listings (a looser cut) are kept, with any size their titles state
    ("90 x 60 cm", "4x3 ft", "24 inch"), for Jev to judge one by one (section 5).
  - An unreadable spine gets the median of the identified books.
  - Every query is cached in `data/price_cache/`.

### Pipeline 2: frontier model (`frontier.run_opus`, `frontier.run_astra`)

- Claude Opus 5.5 runs through `claude -p` with Read, WebSearch and WebFetch. Bash, Edit and
  Write are disallowed.
- It gets every photo, each tagged "room" or "close-up of the <item>", and one prompt asking
  for:
  - a deduplicated inventory
  - spine titles and genres
  - switch, socket and regulator counts per switchboard
  - doors and windows as building fixtures
  - a new price in India per item, with the URL it came from, priced like kind and quality
    (same type, size and grade), marked exact (this model) or closest, with the size of the
    product it priced
  - model numbers and serials off every readable sticker
  - condition, room area, shelf count, and notes for the insurer
- On the merged capture: 43 items in 306 s, reported as $3.23 of usage by `claude -p`. On the
  fresh run after the CTO call: 48 items in 414 s, $3.80.
- **Second pass, one run per object** (`frontier.run_objects`, added after the CTO call). Every
  object on the owner's list (books aside) gets its own `claude -p` run with every photo of it at
  once: its close-ups, and crops (with some room around them) of the largest boxes it was
  detected in, up to 6. The prompt asks for:
  1. its exact identity from every label, sticker and screen; for computers the CPU, GPU, RAM and
     storage, from a label or from the official specification of a model number it read
  2. its dimensions from the manufacturer or a retailer's specification, on the web
  3. its new price in the room's city, like kind and quality, exact or closest, never a used
     listing
  Each answer is tied to its item (`Item.link`), like an owner note, so Jev sees it as a fourth
  reading of that object. Answers are cached by prompt in `out/objects/`, so a replay costs
  nothing. On the bedroom: 26 objects in 451 s, 4 in parallel, $11.66. The laptop came back as
  the 15-fb3185AX read off its label, Ryzen 7 260, RTX 5050, 24 GB, 1 TB, ₹1,31,999 new at Vijay
  Sales, 35.8 x 25.5 x 2.35 cm. The room pass stays, because it finds what the detector missed:
  doors, windows, the MCB box, shoes.
- The raw output is kept in `out/opus_raw.json`.
- `run_astra` is the same prompt through the OpenAI Responses API with `web_search`
  (`gpt-6-astra`). It is written but untested, because the key had no credits.

### Owner: voice and text (`voice.run_items`)

- Whisper large-v3-turbo transcribes each note. ffmpeg decodes it to 16 kHz mono first,
  because Chrome records webm and iPhones record m4a.
- **Prices and ages are read by rules** (`voice.parse_price`, `parse_age`), not by a model:
  - prices: "16K", "1.9 lakhs", "Rs. 2500", "500 rupees", "five hundred rupees"
  - spoken ranges: "fifteen, sixteen thousand" or "15 to 16k" give the midpoint, and the range
    is kept on the item as a note
  - ages: "3 years back", "one month old", "last year"
  - Qwen 2B had invented a ₹12,000 charger and read "40 years back" as one year.
- "Came free" or "company provided" is flagged, and ₹0 is never a price.
- **The owner's price is evidence, not a candidate** (since the CTO call: "the owner obviously
  wants to maximise how much they get"). It is checked against the market price: more than 30
  percent above it asks for a receipt. It is used as the price only when no market source
  priced the item, and then flagged. The age still sets the depreciation.
- Qwen reads only the brand from the text.
- Each owner statement is linked to its item (`Item.link`).

## 5. Jev combines the three (`jev.py`)

Jev (TypeSafe, `jev-1.13.0`) answers typed questions with probabilities and a confidence.
As its docs advise, it only judges; counting, thresholds and arithmetic stay in code.

1. **Links before any guessing:**
   - An owner note joins its item.
   - A frontier item that lists an item's close-up among its photos is that item, if it is
     the same category and shares a word with the item's name. A door in the background of
     the chair's close-up is not the chair.
2. **Similarity filter:**
   - Only pairs of comparable categories are considered. Bedding and furniture are
     comparable, since a bed was filed under both. Building fixtures are never compared
     across categories.
   - Only each item's 3 most similar candidates in each other source are scored.
   - On the merged capture: 109 pairs scored, 231 skipped.
3. **One Score per pair.** The levels are spelled out, because Jev reads literally; a misread
   model name once made it call one laptop two.

   ```
   instructions: {item_a: {laptop, HP, "Vergence", 14 in, photos f1 f2 f3},
                  item_b: {HP Victus 15, 15.6 in, photos f1 f2 f3},
                  question: "Do item_a and item_b describe the same physical object in this room?"}
   criteria:     ["different objects: a different kind, a different brand, or a clearly different item",
                  "possibly the same object, not sure",
                  "the same physical object: same kind and brand, or seen in the same photos;
                   small differences in model name, size, colour or wording are misreadings"]
   ```

   Books get their own levels: the same title, allowing OCR slips and words run together.
4. **Merge rules, in code** (`jev._merge_scored`). A group never holds two items from the
   same source. Pairs merge when:
   - the score is 1.5 or more (Jev says the same object)
   - the score is 0.75 or more and each item is the other's best match
   - each source has exactly one item of this category, unless Jev is confident they
     differ
   - each source has exactly one item of this category, with the same brand, in the same
     photo

   Anything else near a match is flagged as a possible double count.
5. **Per merged item, first round:**
   - a Choice picks which reading identifies it
   - a Score gives its condition
   - a Choice gives the genre for books
6. **Every listing judged against that identity** (`jev.judge_listings`). One Score per listing
   behind a search price, with the identity Jev chose and the size measured in 3D:

   ```
   criteria: ["a different product: another kind of object, or an accessory, spare part, refill or bundle",
              "a similar product: the same kind of object, but a different model, size, material or type",
              "this exact product: same kind, same brand and model (or the same specification when no model
               is known), and about the same size"]
   ```

   Code then prices the source again: the median of the listings of this exact product is the
   **exact** price; failing that, the median of the similar ones is the **closest** price (the
   two fields Alok asked for); the 25th to 75th percentile is the range. For rigid objects measured
   from two views or more, a listing whose stated size is more than 1.8 times off the measured
   size is a different product: like kind and quality includes size. A source left with no listing loses its price, and the market search
   (section 6) tries again with Jev's identity.
7. **Second round: which market price to trust.** A Choice among pipeline 1, the frontier model
   and the market search. The owner's figure is not a candidate:

   ```
   how_to_judge: "A listing judged to be this exact product is the strongest evidence. Next best is the
                  closest similar product of the same type and size. A class estimate with no listing is
                  weaker, and a median over many different models is weakest."
   ```

   Confidence under 0.5 flags the line for review. When Jev is that unsure and the market prices
   are 3 or more times apart (the whiteboard sheet: ₹400 from Opus against a ₹10.6k framed
   board), the line is **held for review**: left out of the total, reported with its range.
8. **Batching:** 40 questions per call, 6 calls in parallel. On the merged capture that was
   236 questions in 7 calls, 85k input tokens, about 5 s and well under a cent. Every call
   (state, questions, answers, model, usage) is kept in `out/runs/<time>/jev_calls.jsonl`.

## 6. Market prices after Jev, for what is still unpriced (`market.py`)

Jev has ranked the three price sources: pipeline 1's search, the frontier model's web price,
and the owner's price from within 2 years. A merged item can still have no price at all:
- the local search found no matching listing
- the frontier model missed the item
- the owner said nothing about it

Each such item is searched once more, with the identity Jev chose (usually a better query than
the local reading), its listings are judged the same way, and the result joins as a **market**
candidate. An item whose local listings Jev judged all wrong gets this second search too. An
unreadable book gets the room's median book price.

**Why both.** At first Serper ran only after Jev, and pipeline 1 gave no prices. That scored
worse, and it departs from the brief, where pipeline 1 produces values for Jev to rank against
Astra's. Replayed on the three saved captures (with the earlier Opus pass):

| Capture | Mean RCV error on recent purchases, Serper only after Jev | Both |
|---|---|---|
| merged | 10.6% | 10.0% |
| video | 13.8% | 10.6% |
| photos | 31.0% | 31.0% |

With three candidates, Jev picked the owner's price for the AC (₹35k) and the table (₹8k),
where it had picked the frontier's before. The after-Jev search then had nothing left to do on
two captures and one item on the third.

## 7. Valuation (`valuation.py`, `prices.acv`, `area.py`)

- **RCV** is the chosen market price times the quantity, with its range and whether it is the
  exact product or the closest.
- **ACV** is `RCV x (1 - min(cap, age / useful life x condition adjustment))`, as US contents
  adjusters depreciate (`prices.DEPRECIATION`, researched 2026-09-27):
  - Claims Pages' depreciation guide (built with adjusters) gives useful lives by category, and
    says an item still working for its purpose is not depreciated past 90 percent. Xactimate
    has a "max depreciation" per carrier and state. Cozmo's CTO: "usually 75 to 80 percent".
    California's 10 CCR 2695.9: depreciation must reflect a measurable loss of value, and
    labour is never depreciated.
  - The table, as defaults for a carrier's own: electronics 80 percent cap (laptop 4 years,
    monitor 6, phone 3), appliances 75 (8 years), furniture 75 (12), bedding 80 (5), decor 75,
    books 50 (they keep value; adjusters often do not depreciate them), and electrical and
    building fixtures 70 (priced with installation, which is not depreciated).
  - The age comes from the owner, if said, and the condition adjusts it: like new counts 0.75
    of the age, fair 1.15, poor 1.3. With no age, the condition stands in for it: like new 10
    percent of the life used, good 35, fair 60, poor 85.
  - Before the CTO call it was a 10 percent floor for everything. The 40-year-old almirah now
    keeps 25 percent of its replacement cost, not 10.
- **Contents** and **building fixtures** (doors, windows, switchboards, the MCB box) are
  totalled apart, because an insurer covers them under different policies.
- **Books** are totalled by genre.
- Lines are flagged when their price confidence is low, a possible double count exists, the
  owner said the item was free or provided, the owner's price is far above the market (a
  receipt is asked for), the measured size does not fit the product the frontier model priced,
  or no source gave a price. Held lines are totalled apart, as a range.
- **Area**, in order of preference:
  1. tape dimensions
  2. a floor plan the floor plan take-home already measured (its ARCore depth tier: 15.68 m²
     against the tape's 15.61 m²)
  3. that pipeline run on these photos (VGGT plus MoGe-2 scale: 11.6 m², too low)
  4. the frontier model's estimate (15.5 m² on the latest pass, 12.5 m² on the one before)

  Every candidate is shown, and the plan picture comes from whichever has one.

## 8. Results and the owner's final review (`web/results.html`)

- Every line shows what each source said and which one Jev trusted, with the photos, the
  candidates, and the Jev probabilities.
- The owner can **Remove** a line, mark it **Same as** another (flagged lines get a suggested
  target), or **Undo**. Totals recompute on the next read, with no re-run.
- Decisions are stored by a stable line key, the sorted member item ids, so they survive
  replays.

## 9. What is saved, and replays

| Artifact | Where | Used for |
|---|---|---|
| Every Serper response | `data/price_cache/*.json` | replays never search twice |
| 3D of the photos and frames | `out/geometry/vggt.npz` | positions and sizes; reused when the photo list is the same |
| Jev's verdict on every listing | `out/listing_verdicts.json`, and on each line's candidates | exact and closest prices |
| Market searches after Jev | `out/market_log.json` | which items were searched, with what query |
| Frontier raw output and parsed items | `out/opus_raw.json`, `out/frontier.json` | `--reuse frontier` |
| Local close-up and spine reading | `out/local_refined.json` | `--reuse refine` (no GPU) |
| Transcripts | `out/transcripts.json` | `--reuse transcripts` |
| Report, pair scores, every Jev call, settings, score | `out/runs/<time>/` | comparing settings run against run |
| Frozen real captures | `data/fixtures/` | the tuning loop |

`uv run room-valuation revalue <capture> --reuse frontier,refine,transcripts` re-runs
matching, Jev and the valuation on saved sources in about a minute, for free. Every fix in
the README's tuning table was found and checked this way.

## 10. Known limits

- **Local-only duplicates** are now merged by 3D position at detection. What 3D cannot catch is
  a false detection at a place of its own: the "wardrobe" was a blurred frame of the curtain.
  Its measured 25 x 44 cm fits no wardrobe listing, so it gets no price and is flagged.
- **3D sizes are estimates, and only for rigid things.** The laptop measured 37 cm against 36,
  the monitor 25 percent small. On the fresh run a bedsheet measured 32 x 45 cm, the charger with
  its cable 26 x 66, a switchboard with its wiring a metre tall, the bed 44 x 14 (seen edge-on).
  So sizes are checked only for furniture, appliances, laptops, monitors, networking, audio and
  kitchenware, shown as a "3D size check" flag, and a line is held on size only when nothing but
  its own crop saw it (not the room pass, no owner note) and the priced product is over 3 times
  the measured size: the blurred curtain the detector called a wardrobe, which the per-object
  pass priced as a ₹18,100 steel almirah.
- **The small VLM copies prompt examples.** On the merged capture the laptop got
  "specs: 1400 W" from the air-fryer example in the close-up prompt. Values equal to a prompt
  example are now dropped. Owner notes and the frontier model outrank the local reading
  anyway.
- **Floor area from phone photos alone is weak** (11.6 m² against 15.6). Use tape
  dimensions or a measured plan.
- **Windows and doors** are the frontier model's supply-plus-install estimates, not
  listings.
- **The depreciation table** is a researched default, not a carrier's own. Replace
  `prices.DEPRECIATION` with the carrier's table.
- **No serial lookup.** Serials are read and kept as evidence; there is no manufacturer API to
  turn one into a specification.
- **One room per capture.** A whole house is several captures; there is no roll-up yet.
- **The GPT-6 Astra backend is untested.**
