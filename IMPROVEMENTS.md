# Improvements after the CTO call (2026-09-26)

Built on the `improvements` branch, 2026-09-27. How each stage works in detail:
[docs/design/pipeline.md](docs/design/pipeline.md).

## Results

The merged bedroom re-detected from its raw photos and video and re-valued from scratch
(capture 20260927-061610-8b4353, run 20260927-095309). Before is the run shown on the call
(20260926-153315).

| | Before (on the call) | After |
|---|---|---|
| RCV / ACV | ₹3.90 / ₹2.82 lakh | ₹3.28 / ₹2.39 lakh |
| Mean RCV error, 4 recent purchases | 15.0% (Jev picked the owner's own price on 3 of 4) | **15.6%, no owner price used** |
| Laptop | ₹1.9 lakh (the owner's word); ₹77k to ₹79k from the market | ₹1,31,999, the exact 15-fb3185AX read off its label |
| Frontier model alone | 30% | 15.6% (per object), 32% (room pass) |
| Local pipeline alone | priced 32 of its items | priced 36 of 39; AC 0%, desk +16%, laptop -55% |
| Lines held for review (out of the total) | none | 5, ₹3.2k to ₹53k (the false "wardrobe", and 4 where Jev was unsure and prices 3 to 15 times apart) |
| Books | 11 of 11 plus 1 flagged | 11 of 11 plus 1 flagged |
| Video frames | 16 (capped) | 30 (by coverage) |
| Frontier model cost | $3.23 | $15.46 ($3.80 room pass, $11.66 per object) |
| Run time | about 5 minutes | about 11 minutes |

Reports: [docs/results/bedroom-after-call/report.md](docs/results/bedroom-after-call/report.md)
(before: [docs/results/bedroom-merged/report.md](docs/results/bedroom-merged/report.md)).

## Demos

Open in a browser from a clone; no server needed. Arrow keys move between the steps.

- [demo/bedroom-after-call/index.html](demo/bedroom-after-call/index.html): after the call, with the new 3D tab, Jev's listing verdicts and the per-object Opus pass
- [demo/bedroom/index.html](demo/bedroom/index.html): before, the run shown on the call
- [demo/bedroom-fresh/index.html](demo/bedroom-fresh/index.html): before, the same inputs re-run from scratch
- [demo/index.html](demo/index.html): all demos

## Improvements, one line each

**Pricing**
- The owner's price is evidence, not a candidate: more than 30% above the market asks for a receipt.
- Jev judges every search listing against the object (this product, similar, different), giving an exact and a closest price with a 25th to 75th range.
- Used, refurbished and open-box listings are dropped: a replacement cost is the price new.
- A line is held for review, out of the total, when Jev is unsure and the prices are 3 or more times apart.
- An electronic item or appliance priced as the closest equivalent is flagged "exact model not seen", with the photo that would fix it.
- A computer with no readable configuration is flagged as priced at the base model.

**Depreciation**
- Straight-line per category with a cap, researched from US adjuster guides (electronics 80%, furniture 75%, fixtures 70%, books 50%), instead of a 10% floor.
- Condition adjusts the age-based rate (an old item kept like new loses less).
- Jev chooses each line's category from every reading, so the useful life and cap follow what the object is (the box bed is furniture, not bedding).

**Reading labels**
- Model, product and serial numbers are read off labels by rules on the OCR text, not by the small vision model.
- A computer's configuration (CPU, GPU, RAM, storage) is read from labels, the frontier model or the owner's words, and searched.
- Labels are read upside down too (180 degrees), and small print in enlarged tiles.
- OCR moved to PP-OCRv6 medium: 81% of known words read against 72%, measured on the room's own photos.
- Qwen3-VL-4B was measured against the 2B on the room's photos and not taken (lower on crops, twice as slow).

**Frontier model**
- Opus now also runs once per object with every photo of it, for its exact identity, dimensions from the web and local price.
- Its answers are cached, so replays cost nothing.

**Local pipeline**
- Each item is read from all its photos at once, like the per-object pass, giving a specific search phrase.
- A brand counts only when printed or confirmed by two readings; otherwise the item is searched without it.
- Filler words ("in India", "for sale") are dropped from searches.

**3D**
- Every detection is placed and measured in 3D (VGGT and MoGe-2), in aligned chunks for any number of frames.
- Duplicates merge by 3D position and size, and two same-named objects far apart stay two.
- Sizes are checked against the priced product only for rigid objects; a line seen only in its own crop whose product is over 3 times its size is held (the blurred curtain called a wardrobe).
- The owner's review carries onto a fresh detection by photo content and 3D position.

**Capture**
- Video frames are kept by coverage with no cap, so a video of any length works.
- The laptop's item page asks for the bottom label or Settings > About.
- Spoken price ranges ("fifteen, sixteen thousand") give the midpoint, with a note.

**Books**
- Run-together partial spine reads ("RONHORSE EDWARD MARSTON") are recognised as the matched book and dropped.

## Known limits

- 3D sizes are unreliable for soft or sprawling objects, so they are not used there.
- The depreciation table is a researched default, to be replaced by a carrier's own.
- Per-object Opus raises the cost to about $15 a room.
- The suitcase's printed "LAX" was taken for a brand by the local pipeline; the line was held, not fixed.
- GPT-6 Astra is still untested (no credits).
