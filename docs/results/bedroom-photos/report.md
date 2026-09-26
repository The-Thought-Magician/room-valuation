# Bedroom, Rourkela: contents valuation

Capture `20260926-072711-873ed5`
- Photos: 8 (room photos and video frames used for detection)
- Owner review: 20 items kept, 5 removed, 3 added, 7 close-ups, 12 voice notes
- Pipeline 2: claude-opus-5-5; Jev scored 90 pairs (similarity filter skipped 202)

## Totals

| | Replacement (RCV) | After depreciation (ACV) | Items |
|---|---|---|---|
| Contents (incl. books) | ₹270,701 | ₹214,677 | 37 |
| Building fixtures | ₹57,509 | ₹22,632 | 9 |
| **Total** | **₹328,210** | **₹237,309** | 46 |

Books: 11, ₹5,517. Lines flagged for review: 20. Possible double counts: ₹590. Owner's review: 0 removed, 0 marked duplicate.

## Floor

**15.61 m² (168 sq ft)**, from tape measurement of this bedroom (floor plan take-home ground truth, 2026-09-20); 426.7 x 365.8 cm, ceiling 312.4 cm

- also 15.68 m² from floor plan pipeline, depth tier (20260920-035737-0c6f2b)
- also 11.0 m² from frontier model estimate from photos

![floor plan](floor_plan.png)

## Items

Price from: which source Jev trusted. Sources: who saw it (local models, frontier model, owner).

| Item | Qty | RCV | ACV | Price from | Local | Frontier | Owner | Flags |
|---|---|---|---|---|---|---|---|---|
| **Contents** | | | | | | | | |
| HP Victus 15 gaming laptop with HP power adapter | 1 | ₹190,000 | ₹186,960 | voice | ₹95,490 | ₹84,990 | ₹190,000 | frontier item matched by the owner's close-up |
| Steel almirah, 2-door, pale green | 1 | ₹18,100 | ₹1,810 | frontier | ₹7,999 | ₹18,100 | – |  |
| Wooden box bed (diwan) with laminate finish | 1 | ₹12,000 | ₹1,200 | frontier | ₹19,190 | ₹12,000 | – | low Jev confidence on price (0.44) |
| Acer monitor, about 24 inch, thin bezel | 1 | ₹11,999 | ₹6,000 | frontier | ₹12,249 | ₹11,999 | – | merged on 'possibly the same' (1.30) as mutual best match; low Jev confidence on price (0.06) |
| Computer desk, black metal frame with laminated top | 1 | ₹6,000 | ₹3,900 | frontier | – | ₹6,000 | – |  |
| Green Soul high-back ergonomic mesh office chair with headrest | 1 | ₹5,500 | ₹3,575 | voice | – | ₹8,490 | ₹5,500 | frontier item matched by the owner's close-up |
| Uppercase hard-shell cabin trolley suitcase, LAX print | 1 | ₹4,200 | ₹1,400 | frontier | – | ₹4,200 | ₹2,500 |  |
| GeoDebt router | 1 | ₹2,500 | ₹1,625 | frontier | ₹2,749 | ₹2,500 | – | low Jev confidence on identity (0.26); low Jev confidence on price (0.08) |
| Printed patchwork bedcover | 1 | ₹2,344 | ₹938 | local | ₹2,344 | ₹700 | – | low Jev confidence on price (0.41) |
| Eyelet curtain panels, brown palm-tree print | 4 | ₹1,800 | ₹720 | frontier | ₹629 | ₹450 | – | frontier item matched by the owner's close-up; low Jev confidence on price (0.14) |
| Razer DeathAdder wired gaming mouse | 1 | ₹1,749 | ₹175 | frontier | ₹5,744 | ₹1,749 | – |  |
| Shoes stored under almirah | 2 | ₹1,600 | ₹640 | frontier | – | ₹800 | – |  |
| Wooden stool with turned legs | 1 | ₹1,500 | ₹150 | frontier | ₹610 | ₹1,500 | – | low Jev confidence on price (0.18) |
| Navy laptop backpack | 1 | ₹1,305 | ₹848 | local | ₹1,305 | ₹1,200 | – | low Jev confidence on price (0.41); owner: free or provided (the owner said so); may not be the owner's to |
| Stainless steel curtain rod with brackets | 2 | ₹1,258 | ₹504 | local | ₹629 | ₹700 | – | frontier item matched by the owner's close-up |
| Pillow with peach cover | 1 | ₹1,030 | ₹412 | local | ₹1,030 | ₹350 | – | low Jev confidence on price (0.38) |
| Folded white printed dohar/blanket | 1 | ₹900 | ₹585 | frontier | – | ₹900 | – |  |
| USB phone charger adapter with braided cable | 1 | ₹600 | ₹390 | frontier | ₹346 | ₹600 | – | low Jev confidence on price (0.15); owner: free or provided (the owner said so); may not be the owner's to |
| Extended gaming mouse pad, anime print | 1 | ₹499 | ₹200 | frontier | – | ₹499 | – |  |
| Wall-mounted whiteboard sheet on PVC rollers | 1 | ₹150 | ₹60 | voice | ₹1,139 | ₹400 | ₹150 | low Jev confidence on price (0.30) |
| Mop/broom with long handle | 1 | ₹150 | ₹60 | frontier | – | ₹150 | – |  |
| **Building fixtures** | | | | | | | | |
| Window with wooden frame, glass shutters and steel grill (above bed) | 1 | ₹18,000 | ₹7,200 | frontier | – | ₹18,000 | – |  |
| Window with wooden frame, glass shutters and steel grill (side wall) | 1 | ₹16,000 | ₹6,400 | frontier | – | ₹16,000 | – |  |
| Wooden panel door with frame and hardware | 1 | ₹15,000 | ₹6,000 | frontier | – | ₹15,000 | – |  |
| PVC folding door, beige slatted | 1 | ₹5,000 | ₹2,000 | frontier | – | ₹5,000 | – |  |
| Havells MCB enclosure with 2 single-pole 25A MCBs | 1 | ₹1,050 | ₹420 | frontier | – | ₹1,050 | – |  |
| Switchboard with round surface fittings on wooden batten board | 1 | ₹900 | ₹135 | frontier | – | ₹900 | – |  |
| Switchboard beside router (old non-modular board) | 1 | ₹590 | ₹89 | local | ₹590 | ₹1,800 | – | possible double count with Small white modular switchboard right of wi |
| Power extension board, 4-way, white with red cord | 1 | ₹519 | ₹208 | local | ₹519 | ₹450 | – | low Jev confidence on price (0.44) |
| Small white modular switchboard right of window | 1 | ₹450 | ₹180 | frontier | – | ₹450 | – |  |
| **Books** | | | | | | | | |
| Living nonviolent communication (Marshall B. Rosenberg) · self_help | 1 | ₹951 | ₹618 | local | ₹951 | ₹499 | – |  |
| A History of the World in 10 1/2 Chapters (Julian Barnes) · fiction | 1 | ₹799 | ₹320 | local | ₹799 | ₹499 | – |  |
| The Hare with Amber Eyes Edmund de Waal (author not read) · biography_memoir | 1 | ₹699 | ₹280 | frontier | ₹316 | ₹699 | – |  |
| Annie May's Black Book (Debby Holt) · fiction | 1 | ₹695 | ₹278 | local | ₹695 | ₹499 | – |  |
| Iron Horse (Keith Miles) · mystery_thriller | 1 | ₹599 | ₹240 | frontier | – | ₹599 | – | merged on 'possibly the same' (1.14) as mutual best match |
| Rock Paper Scissors (Alice Feeney) · mystery_thriller | 1 | ₹400 | ₹160 | frontier | ₹876 | ₹400 | – |  |
| The 80/20 Principle (Richard Koch) · self_help | 1 | ₹316 | ₹205 | local | ₹316 | ₹499 | – | low Jev confidence on identity (0.35); low Jev confidence on price (0.42) |
| Antony and Cleopatra (William Shakespeare) · classics | 1 | ₹304 | ₹122 | local | ₹304 | ₹150 | – | low Jev confidence on identity (0.37) |
| The Great Gatsby (F. Scott Fitzgerald) · fiction | 1 | ₹299 | ₹120 | frontier | ₹154 | ₹299 | – | low Jev confidence on identity (0.07) |
| Torment (Lauren Kate) · fiction | 1 | ₹295 | ₹118 | local | ₹295 | ₹450 | – | low Jev confidence on identity (0.27) |
| The thread (Victoria Hislop) · fiction | 1 | ₹160 | ₹64 | local | ₹160 | ₹499 | – |  |

## Against the owner's ground truth

10/13 ground-truth items found; 3 with a recent purchase price, mean |RCV error| 31.0%

| Owner's item | Paid | Age (y) | Local | Frontier | Owner | Jev chose | RCV | Error |
|---|---|---|---|---|---|---|---|---|
| HP Victus gaming laptop (Ryzen 7 260, RTX 5050) | ₹190,000 | 0.08 | ₹95,490 | ₹84,990 | ₹190,000 | voice | ₹190,000 | +0.0% |
| Acer 24 inch monitor | ₹16,000 | 3 | ₹12,249 | ₹11,999 | – | frontier | ₹11,999 | – |
| chair | ₹5,500 | – | – | ₹8,490 | ₹5,500 | voice | ₹5,500 | – |
| L-shaped study table (desk) | ₹8,000 | 0.75 | – | ₹6,000 | – | frontier | ₹6,000 | -25.0% |
| split AC | ₹35,000 | 1 | – | – | – | – | – | not found |
| bed | ₹450 | 35 | ₹19,190 | ₹12,000 | – | frontier | ₹12,000 | – |
| steel almirah | ₹350 | 40 | ₹7,999 | ₹18,100 | – | frontier | ₹18,100 | – |
| Razer DeathAdder mouse | ₹2,500 | 4 | ₹5,744 | ₹1,749 | – | frontier | ₹1,749 | – |
| suitcase | ₹2,500 | 2 | – | ₹4,200 | ₹2,500 | frontier | ₹4,200 | +68.0% |
| stool | ₹600 | 8 | ₹610 | ₹1,500 | – | frontier | ₹1,500 | – |
| whiteboard sheet | ₹150 | – | – | – | – | – | – | not found |
| JioFiber router | – | – | ₹2,749 | ₹2,500 | – | frontier | ₹2,500 | – |
| Good Knight liquid mosquito repellent | – | – | – | – | – | – | – | not found |

Error is only computed where the purchase is within 2 years, so the price paid is a fair replacement cost.

## How the sources ranked (Jev)

| Source | Items found | Found alone | Identity chosen | Price chosen |
|---|---|---|---|---|
| local | 30 | 0 | 4/30 | 13/26 |
| frontier | 41 | 11 | 25/30 | 12/28 |
| voice | 12 | 0 | 1/12 | 3/4 |
