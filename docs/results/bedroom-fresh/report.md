# Bedroom, Rourkela: contents valuation

Capture `20260926-154153-785cb7`, merged from 20260926-090044-d552ae
- Photos: 24 (room photos and video frames used for detection)
- Owner review: 30 items kept, 21 removed, 3 added, 10 close-ups, 12 voice notes
- Pipeline 2: claude-opus-5-5; Jev scored 110 pairs (similarity filter skipped 303)
- Market prices after Jev: 0 items searched on Serper, 0 priced, 0 unreadable books at the room median

## Totals

| | Replacement (RCV) | After depreciation (ACV) | Items |
|---|---|---|---|
| Contents (incl. books) | ₹337,035 | ₹258,144 | 51 |
| Building fixtures | ₹84,823 | ₹41,466 | 12 |
| **Total** | **₹421,858** | **₹299,610** | 63 |

Books: 12, ₹6,197. Lines flagged for review: 27. Possible double counts: ₹2,977. Owner's review: 0 removed, 0 marked duplicate.

## Floor

**15.61 m² (168 sq ft)**, from tape measurement of this bedroom (floor plan take-home ground truth, 2026-09-20); 426.7 x 365.8 cm, ceiling 312.4 cm

- also 15.68 m² from floor plan pipeline, depth tier (20260920-035737-0c6f2b)
- also 15.5 m² from frontier model estimate from photos

![floor plan](floor_plan.png)

## Items

Price candidates: Local (pipeline 1's Serper search), Frontier (the frontier model's web price), Owner (a price paid within 2 years), Market (a second search after Jev, only for what was still unpriced). Price from: the one Jev trusted.

| Item | Qty | RCV | ACV | Price from | Local | Frontier | Owner | Market | Flags |
|---|---|---|---|---|---|---|---|---|---|
| **Contents** | | | | | | | | | |
| HP Victus 15 gaming laptop (AMD Ryzen, NVIDIA GeForce RTX) | 1 | ₹190,000 | ₹186,960 | voice | ₹93,437 | ₹65,000 | ₹190,000 | – | frontier item matched by the owner's close-up |
| Carrier split air conditioner (indoor unit, protective film still on) | 1 | ₹35,890 | ₹31,404 | frontier | ₹32,745 | ₹35,890 | ₹35,000 | – | frontier item matched by the owner's close-up; low Jev confidence on price (0.25) |
| wardrobe | 1 | ₹20,094 | ₹3,014 | local | ₹20,094 | – | – | – |  |
| Steel almirah, 2 door, pistachio green | 1 | ₹15,000 | ₹1,500 | frontier | ₹4,149 | ₹15,000 | – | – | low Jev confidence on identity (0.38) |
| Wooden box bed (double), laminated wood finish | 1 | ₹14,000 | ₹1,400 | frontier | ₹20,990 | ₹14,000 | – | – | low Jev confidence on price (0.42) |
| Acer 24 inch class monitor, thin bezel, red accent on stand | 1 | ₹11,249 | ₹5,624 | local | ₹11,249 | ₹8,635 | – | – | low Jev confidence on price (0.26) |
| Large L-shaped computer desk, black top, black metal frame | 1 | ₹8,000 | ₹7,400 | voice | ₹9,999 | ₹8,999 | ₹8,000 | – |  |
| Green Soul high-back ergonomic mesh office chair | 1 | ₹5,500 | ₹3,575 | voice | – | ₹15,437 | ₹5,500 | – | frontier item matched by the owner's close-up |
| Mattress on the bed (under the bedsheet) | 1 | ₹5,500 | ₹3,575 | frontier | – | ₹5,500 | – | – |  |
| Uppercase hard-shell trolley suitcase, LAX airport print | 1 | ₹4,200 | ₹1,400 | frontier | – | ₹4,200 | ₹2,500 | – | merged on 'possibly the same' (1.36) as mutual best match |
| GeoDebt router | 1 | ₹2,500 | ₹1,625 | frontier | ₹2,099 | ₹2,500 | – | – | low Jev confidence on identity (0.40); low Jev confidence on price (0.27) |
| bedspread | 1 | ₹1,990 | ₹796 | local | ₹1,990 | – | – | – |  |
| Razer DeathAdder Essential wired gaming mouse | 1 | ₹1,749 | ₹175 | frontier | ₹6,173 | ₹1,749 | – | – |  |
| Shoes stored under the almirah | 2 | ₹1,600 | ₹640 | frontier | – | ₹800 | – | – |  |
| Eyelet curtain panels, brown palm-tree print | 4 | ₹1,596 | ₹640 | frontier | ₹439 | ₹399 | – | – | frontier item matched by the owner's close-up; low Jev confidence on price (0.11) |
| Navy blue laptop backpack | 1 | ₹1,500 | ₹975 | frontier | ₹502 | ₹1,500 | – | – | low Jev confidence on price (0.18); owner: free or provided (the owner said so); may not be the owner's to |
| curtain | 1 | ₹1,219 | ₹183 | local | ₹1,219 | – | – | – |  |
| pillow | 1 | ₹1,064 | ₹160 | local | ₹1,064 | – | – | – | possible double count with Pillow with peach cover (opus-12), Jev 0.84 |
| Extension board / spike guard, white | 2 | ₹900 | ₹360 | frontier | – | ₹450 | – | – |  |
| White printed dohar / light quilt, folded | 1 | ₹899 | ₹584 | frontier | – | ₹899 | – | – |  |
| Stainless steel curtain rod with brackets | 2 | ₹878 | ₹352 | local | ₹439 | ₹650 | – | – | frontier item matched by the owner's close-up; low Jev confidence on identity (0.29) |
| Pillow with peach cover | 1 | ₹838 | ₹545 | local | ₹838 | ₹349 | – | – | low Jev confidence on price (0.49) |
| USB phone charger (white) with braided cable | 1 | ₹810 | ₹526 | local | ₹810 | ₹599 | – | – | merged on 'possibly the same' (1.33) as mutual best match; low Jev confidence on price (0.17) |
| Printed cotton double bedsheet, red, black and beige patchwork | 1 | ₹799 | ₹519 | local | ₹799 | ₹699 | – | – |  |
| Wooden stool with turned legs | 1 | ₹610 | ₹61 | local | ₹610 | ₹1,500 | – | – | low Jev confidence on price (0.08) |
| Whiteboard sheet on PVC rods, taped to wall | 1 | ₹450 | ₹180 | frontier | – | ₹450 | – | – |  |
| Extended gaming mouse pad, anime print | 1 | ₹399 | ₹259 | frontier | – | ₹399 | – | – |  |
| LED tube / batten light on wall | 1 | ₹399 | ₹259 | frontier | – | ₹399 | – | – |  |
| Black remote control with sleep and boost keys (fan style remote) | 1 | ₹350 | ₹228 | frontier | – | ₹350 | – | – |  |
| tube light | 1 | ₹296 | ₹44 | local | ₹296 | – | – | – |  |
| Floor mop / broom (leaning in corner) | 1 | ₹250 | ₹100 | frontier | – | ₹250 | – | – |  |
| Good Knight Flash liquid vaporiser mosquito repellent machine with ref | 1 | ₹159 | ₹103 | local | ₹159 | ₹99 | – | – | frontier item matched by the owner's close-up |
| Yellow LED bulb in wall batten holder | 1 | ₹150 | ₹60 | frontier | – | ₹150 | – | – |  |
| **Building fixtures** | | | | | | | | | |
| Wooden panelled door with frame | 1 | ₹18,000 | ₹11,700 | frontier | – | ₹18,000 | – | – |  |
| Window above the bed: wooden frame, glass shutters, MS grill | 1 | ₹16,000 | ₹6,400 | frontier | – | ₹16,000 | – | – |  |
| Flush door, orange finish, with wooden frame and lever lock | 1 | ₹14,000 | ₹9,100 | frontier | – | ₹14,000 | – | – |  |
| Window below the AC: wooden frame, glass shutters, MS grill | 1 | ₹13,000 | ₹5,200 | frontier | – | ₹13,000 | – | – |  |
| Louvred wooden door / shutter, olive finish | 1 | ₹12,000 | ₹4,800 | frontier | – | ₹12,000 | – | – |  |
| whiteboard | 1 | ₹8,140 | ₹3,256 | local | ₹8,140 | – | ₹150 | – | low Jev confidence on identity (0.26); low Jev confidence on price (0.32) |
| Havells MCB enclosure with 2 x SP B25 MCBs | 1 | ₹1,000 | ₹400 | frontier | – | ₹1,000 | – | – |  |
| Old wooden switchboard with round Bakelite fittings | 1 | ₹700 | ₹105 | frontier | – | ₹700 | – | – |  |
| switch | 1 | ₹655 | ₹98 | local | ₹655 | – | – | – | possible double count with Switchboard beside router (sheet board, non |
| Switchboard beside router (sheet board, non-modular) | 1 | ₹590 | ₹236 | local | ₹590 | ₹1,500 | – | – | possible double count with Old wooden switchboard with round Bakelite  |
| extension board | 1 | ₹499 | ₹75 | local | ₹499 | – | – | – |  |
| Modular switch plate near door | 1 | ₹239 | ₹96 | local | ₹239 | ₹800 | – | – | merged on 'possibly the same' (1.16) as mutual best match; possible double count with Switchboard beside router (sheet board, non |
| **Books** | | | | | | | | | |
| Living nonviolent communication (Marshall B. Rosenberg) · self_help | 1 | ₹950 | ₹618 | local | ₹950 | ₹499 | – | – |  |
| A History of the World in 10 1/2 Chapters (Julian Barnes) · fiction | 1 | ₹799 | ₹320 | local | ₹799 | ₹499 | – | – |  |
| Rock Paper Scissors (Alice Feeney) · mystery_thriller | 1 | ₹699 | ₹280 | local | ₹699 | ₹399 | – | – |  |
| Annie May's Black Book (Debby Holt) · fiction | 1 | ₹695 | ₹278 | local | ₹695 | ₹499 | – | – |  |
| The thread (Victoria Hislop) · fiction | 1 | ₹499 | ₹200 | frontier | – | ₹499 | – | – |  |
| Iron Horse (Keith Miles) · mystery_thriller | 1 | ₹499 | ₹200 | frontier | – | ₹499 | – | – | merged on 'possibly the same' (1.41) as mutual best match |
| The Hare with Amber Eyes (author not read) · biography_memoir | 1 | ₹429 | ₹172 | local | ₹429 | ₹599 | – | – | low Jev confidence on price (0.31) |
| unidentified book | 1 | ₹429 | ₹279 | local | ₹429 | – | – | – | possible double count with Torment (opus-36), Jev 1.48 |
| Torment (Lauren Kate) · fiction | 1 | ₹383 | ₹153 | frontier | ₹325 | ₹383 | – | – | low Jev confidence on identity (0.18); low Jev confidence on price (0.25) |
| The 80/20 Principle (Richard Koch) · business_economics | 1 | ₹366 | ₹238 | local | ₹366 | ₹550 | – | – | low Jev confidence on identity (0.05); low Jev confidence on price (0.01) |
| The Great Gatsby (F. Scott Fitzgerald) · fiction | 1 | ₹299 | ₹120 | frontier | ₹127 | ₹299 | – | – | low Jev confidence on identity (0.30); low Jev confidence on price (0.43) |
| Antony and Cleopatra (William Shakespeare) · classics | 1 | ₹150 | ₹60 | frontier | ₹409 | ₹150 | – | – | low Jev confidence on price (0.19) |

## Against the owner's ground truth

13/13 ground-truth items found; 4 with a recent purchase price, mean |RCV error| 17.6%

| Owner's item | Paid | Age (y) | Local | Frontier | Owner | Market | Chosen | RCV | Error |
|---|---|---|---|---|---|---|---|---|---|
| HP Victus gaming laptop (Ryzen 7 260, RTX 5050) | ₹190,000 | 0.08 | ₹93,437 | ₹65,000 | ₹190,000 | – | voice | ₹190,000 | +0.0% |
| Acer 24 inch monitor | ₹16,000 | 3 | ₹11,249 | ₹8,635 | – | – | local | ₹11,249 | – |
| chair | ₹5,500 | – | – | ₹15,437 | ₹5,500 | – | voice | ₹5,500 | – |
| L-shaped study table (desk) | ₹8,000 | 0.75 | ₹9,999 | ₹8,999 | ₹8,000 | – | voice | ₹8,000 | +0.0% |
| split AC | ₹35,000 | 1 | ₹32,745 | ₹35,890 | ₹35,000 | – | frontier | ₹35,890 | +2.5% |
| bed | ₹450 | 35 | ₹20,990 | ₹14,000 | – | – | frontier | ₹14,000 | – |
| steel almirah | ₹350 | 40 | ₹4,149 | ₹15,000 | – | – | frontier | ₹15,000 | – |
| Razer DeathAdder mouse | ₹2,500 | 4 | ₹6,173 | ₹1,749 | – | – | frontier | ₹1,749 | – |
| suitcase | ₹2,500 | 2 | – | ₹4,200 | ₹2,500 | – | frontier | ₹4,200 | +68.0% |
| stool | ₹600 | 8 | ₹610 | ₹1,500 | – | – | local | ₹610 | – |
| whiteboard sheet | ₹150 | – | ₹8,140 | – | ₹150 | – | local | ₹8,140 | – |
| JioFiber router | – | – | ₹2,099 | ₹2,500 | – | – | frontier | ₹2,500 | – |
| Good Knight liquid mosquito repellent | – | – | ₹159 | ₹99 | – | – | local | ₹159 | – |

Error is only computed where the purchase is within 2 years, so the price paid is a fair replacement cost.

## How the sources ranked (Jev)

| Source | Items found | Found alone | Identity chosen | Price chosen |
|---|---|---|---|---|
| local | 41 | 8 | 5/33 | 16/28 |
| frontier | 48 | 16 | 27/32 | 11/29 |
| voice | 14 | 0 | 1/14 | 3/6 |
| market | 0 | 0 | 0/0 | 0/0 |
