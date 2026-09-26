# Bedroom, Rourkela: contents valuation

Capture `20260926-090044-d552ae`, merged from 20260926-072711-873ed5, 20260926-080711-5034d5
- Photos: 24 (room photos and video frames used for detection)
- Owner review: 30 items kept, 21 removed, 3 added, 10 close-ups, 12 voice notes
- Pipeline 2: claude-opus-5-5; Jev scored 109 pairs (similarity filter skipped 231)
- Market prices after Jev: 0 items searched on Serper, 0 priced, 0 unreadable books at the room median

## Totals

| | Replacement (RCV) | After depreciation (ACV) | Items |
|---|---|---|---|
| Contents (incl. books) | ₹315,661 | ₹249,328 | 44 |
| Building fixtures | ₹73,884 | ₹32,593 | 11 |
| **Total** | **₹389,545** | **₹281,921** | 55 |

Books: 12, ₹5,778. Lines flagged for review: 31. Possible double counts: ₹4,086. Owner's review: 0 removed, 0 marked duplicate.

## Floor

**15.61 m² (168 sq ft)**, from tape measurement of this bedroom (floor plan take-home ground truth, 2026-09-20); 426.7 x 365.8 cm, ceiling 312.4 cm

- also 15.68 m² from floor plan pipeline, depth tier (20260920-035737-0c6f2b)
- also 11.62 m² from floor plan pipeline, video tier
- also 15.5 m² from frontier model estimate from photos

![floor plan](floor_plan.png)

## Items

Price candidates: Local (pipeline 1's Serper search), Frontier (the frontier model's web price), Owner (a price paid within 2 years), Market (a second search after Jev, only for what was still unpriced). Price from: the one Jev trusted.

| Item | Qty | RCV | ACV | Price from | Local | Frontier | Owner | Market | Flags |
|---|---|---|---|---|---|---|---|---|---|
| **Contents** | | | | | | | | | |
| HP Victus 15 gaming laptop | 1 | ₹190,000 | ₹186,960 | voice | ₹77,245 | ₹78,858 | ₹190,000 | – | frontier item matched by the owner's close-up |
| Carrier split air conditioner (indoor unit, with remote) | 1 | ₹35,000 | ₹30,625 | voice | ₹32,745 | ₹35,890 | ₹35,000 | – | frontier item matched by the owner's close-up; low Jev confidence on price (0.35) |
| wardrobe | 1 | ₹20,384 | ₹3,058 | local | ₹20,384 | – | – | – |  |
| Steel almirah, 2 door | 1 | ₹12,000 | ₹1,200 | frontier | ₹7,999 | ₹12,000 | – | – | low Jev confidence on identity (0.49) |
| Wooden box bed / diwan | 1 | ₹9,490 | ₹949 | frontier | ₹19,190 | ₹9,490 | – | – | low Jev confidence on price (0.42) |
| Acer 24 inch class monitor (Nitro-style stand) | 1 | ₹8,635 | ₹4,318 | frontier | ₹12,249 | ₹8,635 | – | – |  |
| L-shaped study / computer table | 1 | ₹8,000 | ₹7,400 | voice | ₹2,860 | ₹7,999 | ₹8,000 | – | frontier item matched by the owner's close-up |
| Green Soul high-back ergonomic mesh chair | 1 | ₹5,500 | ₹3,575 | voice | – | ₹8,190 | ₹5,500 | – | frontier item matched by the owner's close-up |
| Uppercase hard-shell trolley suitcase, LAX print | 1 | ₹4,000 | ₹1,333 | frontier | – | ₹4,000 | ₹2,500 | – | merged on 'possibly the same' (1.26) as mutual best match |
| GeoDebt router | 1 | ₹2,500 | ₹1,625 | frontier | ₹2,035 | ₹2,500 | – | – | low Jev confidence on identity (0.40); low Jev confidence on price (0.43) |
| Razer gaming mouse (DeathAdder Essential style) | 1 | ₹1,749 | ₹175 | frontier | ₹4,772 | ₹1,749 | – | – |  |
| Eyelet curtain panel, palm-beach print, brown | 4 | ₹1,400 | ₹560 | frontier | ₹309 | ₹350 | – | – | frontier item matched by the owner's close-up; low Jev confidence on price (0.25) |
| pillow | 1 | ₹1,399 | ₹210 | local | ₹1,399 | – | – | – | possible double count with Pillow with peach cover (opus-19), Jev 0.93 |
| Laptop backpack, navy | 1 | ₹1,305 | ₹848 | local | ₹1,305 | ₹1,200 | – | – | low Jev confidence on price (0.04); owner: free or provided (the owner said so); may not be the owner's to |
| Patchwork bedsheet | 1 | ₹1,249 | ₹812 | local | ₹1,249 | ₹700 | – | – | low Jev confidence on price (0.04) |
| Wooden stool with turned legs | 1 | ₹1,200 | ₹120 | frontier | ₹610 | ₹1,200 | – | – | low Jev confidence on price (0.20) |
| Pillow with peach cover | 1 | ₹1,030 | ₹412 | local | ₹1,030 | ₹350 | – | – |  |
| Folded dohar / light blanket, white with grey print | 1 | ₹800 | ₹520 | frontier | – | ₹800 | – | – |  |
| bedspread | 1 | ₹774 | ₹310 | local | ₹774 | – | – | – | possible double count with Patchwork bedsheet (opus-18), Jev 1.27 |
| USB wall charger with braided cable | 1 | ₹693 | ₹450 | local | ₹693 | ₹500 | – | – | low Jev confidence on price (0.23); owner: free or provided (the owner said so); may not be the owner's to |
| curtain | 1 | ₹629 | ₹94 | local | ₹629 | – | – | – |  |
| Steel curtain rod with brackets | 2 | ₹618 | ₹248 | local | ₹309 | ₹600 | – | – | frontier item matched by the owner's close-up; low Jev confidence on price (0.26) |
| Extended gaming mouse pad, anime print | 1 | ₹499 | ₹324 | frontier | – | ₹499 | – | – |  |
| Wall light fitting above the desk | 1 | ₹300 | ₹195 | frontier | – | ₹300 | – | – |  |
| tube light | 1 | ₹299 | ₹45 | local | ₹299 | – | – | – |  |
| Godrej Good Knight Good Knight Flash liquid vaporiser | 1 | ₹160 | ₹104 | local | ₹160 | ₹110 | – | – | frontier item matched by the owner's close-up; low Jev confidence on identity (0.45) |
| Roll-up whiteboard sheet on PVC rods | 1 | ₹150 | ₹60 | voice | ₹10,637 | ₹400 | ₹150 | – | low Jev confidence on price (0.29) |
| LED bulb on wall batten holder | 1 | ₹120 | ₹48 | frontier | – | ₹120 | – | – |  |
| **Building fixtures** | | | | | | | | | |
| Window above the bed, wooden frame, glass shutters, MS grill | 1 | ₹22,000 | ₹8,800 | frontier | – | ₹22,000 | – | – |  |
| Window beside the MCB box, wooden frame, glass shutters, MS grill | 1 | ₹22,000 | ₹8,800 | frontier | – | ₹22,000 | – | – |  |
| Panel door, natural wood finish, with frame | 1 | ₹14,000 | ₹9,100 | frontier | – | ₹14,000 | – | – |  |
| Flush door, orange laminate, with wooden frame and lever lock | 1 | ₹12,000 | ₹4,800 | frontier | – | ₹12,000 | – | – |  |
| Havells MCB enclosure with 2 Havells Eurobreaker MCBs | 1 | ₹900 | ₹360 | frontier | – | ₹900 | – | – | merged on 'possibly the same' (1.42) as mutual best match |
| Extension board, multi-socket with switches | 2 | ₹900 | ₹360 | frontier | ₹628 | ₹450 | – | – | low Jev confidence on price (0.08) |
| switch | 1 | ₹655 | ₹98 | local | ₹655 | – | – | – | possible double count with Switchboard by the router (piano switches,  |
| Old wooden switchboard with round bakelite fittings | 1 | ₹600 | ₹90 | frontier | – | ₹600 | – | – |  |
| Switchboard by the router (piano switches, fan regulator) | 1 | ₹590 | ₹89 | local | ₹590 | ₹1,500 | – | – | possible double count with Old wooden switchboard with round bakelite  |
| White modular switchboard near the door | 1 | ₹239 | ₹96 | local | ₹239 | ₹600 | – | – | merged on 'possibly the same' (1.39) as mutual best match; possible double count with Switchboard by the router (piano switches,  |
| **Books** | | | | | | | | | |
| Living nonviolent communication (Marshall B. Rosenberg) · self_help | 1 | ₹951 | ₹618 | local | ₹951 | ₹399 | – | – |  |
| Rock Paper Scissors (Alice Feeney) · mystery_thriller | 1 | ₹876 | ₹350 | local | ₹876 | ₹180 | – | – | low Jev confidence on price (0.48) |
| A History of the World in 10 1/2 Chapters (Julian Barnes) · fiction | 1 | ₹799 | ₹320 | local | ₹799 | ₹450 | – | – |  |
| Annie May's Black Book (Debby Holt) · fiction | 1 | ₹695 | ₹278 | local | ₹695 | ₹350 | – | – | low Jev confidence on identity (0.43) |
| Iron Horse (Keith Miles) · mystery_thriller | 1 | ₹450 | ₹180 | frontier | – | ₹450 | – | – | merged on 'possibly the same' (1.48) as mutual best match |
| The Hare with Amber Eyes (author not read) · biography_memoir | 1 | ₹429 | ₹172 | local | ₹429 | ₹499 | – | – |  |
| unidentified book | 1 | ₹429 | ₹279 | local | ₹429 | – | – | – | possible double count with Torment (opus-32), Jev 1.40 |
| The 80/20 Principle (Richard Koch) · self_help | 1 | ₹376 | ₹244 | frontier | ₹316 | ₹376 | – | – | low Jev confidence on identity (0.39); low Jev confidence on price (0.21) |
| Torment (Lauren Kate) · fiction | 1 | ₹333 | ₹133 | frontier | ₹295 | ₹333 | – | – | low Jev confidence on identity (0.21); low Jev confidence on price (0.12) |
| The thread (Victoria Hislop) · fiction | 1 | ₹160 | ₹64 | local | ₹160 | ₹450 | – | – |  |
| The Great Gatsby (F. Scott Fitzgerald) · fiction | 1 | ₹154 | ₹62 | local | ₹154 | ₹250 | – | – | low Jev confidence on price (0.10) |
| Antony and Cleopatra (William Shakespeare) · classics | 1 | ₹126 | ₹50 | frontier | ₹304 | ₹126 | – | – | low Jev confidence on price (0.42) |

## Against the owner's ground truth

13/13 ground-truth items found; 4 with a recent purchase price, mean |RCV error| 15.0%

| Owner's item | Paid | Age (y) | Local | Frontier | Owner | Market | Chosen | RCV | Error |
|---|---|---|---|---|---|---|---|---|---|
| HP Victus gaming laptop (Ryzen 7 260, RTX 5050) | ₹190,000 | 0.08 | ₹77,245 | ₹78,858 | ₹190,000 | – | voice | ₹190,000 | +0.0% |
| Acer 24 inch monitor | ₹16,000 | 3 | ₹12,249 | ₹8,635 | – | – | frontier | ₹8,635 | – |
| chair | ₹5,500 | – | – | ₹8,190 | ₹5,500 | – | voice | ₹5,500 | – |
| L-shaped study table (desk) | ₹8,000 | 0.75 | ₹2,860 | ₹7,999 | ₹8,000 | – | voice | ₹8,000 | +0.0% |
| split AC | ₹35,000 | 1 | ₹32,745 | ₹35,890 | ₹35,000 | – | voice | ₹35,000 | +0.0% |
| bed | ₹450 | 35 | ₹19,190 | ₹9,490 | – | – | frontier | ₹9,490 | – |
| steel almirah | ₹350 | 40 | ₹7,999 | ₹12,000 | – | – | frontier | ₹12,000 | – |
| Razer DeathAdder mouse | ₹2,500 | 4 | ₹4,772 | ₹1,749 | – | – | frontier | ₹1,749 | – |
| suitcase | ₹2,500 | 2 | – | ₹4,000 | ₹2,500 | – | frontier | ₹4,000 | +60.0% |
| stool | ₹600 | 8 | ₹610 | ₹1,200 | – | – | frontier | ₹1,200 | – |
| whiteboard sheet | ₹150 | – | ₹10,637 | ₹400 | ₹150 | – | voice | ₹150 | – |
| JioFiber router | – | – | ₹2,035 | ₹2,500 | – | – | frontier | ₹2,500 | – |
| Good Knight liquid mosquito repellent | – | – | ₹160 | ₹110 | – | – | local | ₹160 | – |

Error is only computed where the purchase is within 2 years, so the price paid is a fair replacement cost.

## How the sources ranked (Jev)

| Source | Items found | Found alone | Identity chosen | Price chosen |
|---|---|---|---|---|
| local | 41 | 7 | 3/34 | 15/30 |
| frontier | 43 | 9 | 30/34 | 12/32 |
| voice | 14 | 0 | 1/14 | 5/6 |
| market | 0 | 0 | 0/0 | 0/0 |
