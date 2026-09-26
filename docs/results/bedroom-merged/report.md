# Bedroom, Rourkela: contents valuation

Capture `20260926-090044-d552ae`, merged from 20260926-072711-873ed5, 20260926-080711-5034d5
- Photos: 24 (room photos and video frames used for detection)
- Owner review: 29 items kept, 21 removed, 2 added, 9 close-ups, 12 voice notes
- Pipeline 2: claude-opus-5-5; Jev scored 118 pairs (similarity filter skipped 334)

## Totals

| | Replacement (RCV) | After depreciation (ACV) | Items |
|---|---|---|---|
| Contents (incl. books) | ₹341,163 | ₹256,935 | 47 |
| Building fixtures | ₹111,593 | ₹54,277 | 12 |
| **Total** | **₹452,756** | **₹311,212** | 59 |

Books: 12, ₹5,573. Lines flagged for review: 29. Possible double counts: ₹22,532. Owner's review: 0 removed, 0 marked duplicate.

## Floor

**15.61 m² (168 sq ft)**, from tape measurement of this bedroom (floor plan take-home ground truth, 2026-09-20); 426.7 x 365.8 cm, ceiling 312.4 cm

- also 15.68 m² from floor plan pipeline, depth tier (20260920-035737-0c6f2b)
- also 11.62 m² from floor plan pipeline, video tier
- also 12.5 m² from frontier model estimate from photos

![floor plan](floor_plan.png)

## Items

Price from: which source Jev trusted. Sources: who saw it (local models, frontier model, owner).

| Item | Qty | RCV | ACV | Price from | Local | Frontier | Owner | Flags |
|---|---|---|---|---|---|---|---|---|
| **Contents** | | | | | | | | |
| HP Victus 15 gaming laptop (AMD Ryzen, NVIDIA GeForce RTX) | 1 | ₹190,000 | ₹186,960 | voice | ₹77,245 | ₹76,021 | ₹190,000 | frontier item matched by the owner's close-up |
| Carrier split air conditioner, indoor unit (with remote) | 1 | ₹35,000 | ₹30,625 | voice | ₹32,900 | ₹35,890 | ₹35,000 | frontier item matched by the owner's close-up; low Jev confidence on price (0.34) |
| wardrobe | 1 | ₹20,384 | ₹3,058 | local | ₹20,384 | – | – |  |
| Steel almirah, 2-door, light green | 1 | ₹18,100 | ₹1,810 | frontier | ₹7,999 | ₹18,100 | – | low Jev confidence on identity (0.36) |
| Box bed / diwan, laminated engineered wood, on castors | 1 | ₹17,989 | ₹1,799 | frontier | ₹19,190 | ₹17,989 | – | possible double count with Foam mattress, double (under bedsheet) (opu; low Jev confidence on price (0.49) |
| Acer flat-panel monitor, about 24 inch, resolution unknown | 1 | ₹12,249 | ₹6,124 | local | ₹12,249 | ₹12,999 | – | low Jev confidence on identity (0.27); low Jev confidence on price (0.26) |
| L-shaped computer desk, black laminated top on black metal frame | 1 | ₹8,000 | ₹7,400 | voice | ₹2,860 | ₹12,000 | ₹8,000 |  |
| Green Soul high-back ergonomic mesh chair with headrest | 1 | ₹5,500 | ₹3,575 | voice | – | ₹8,499 | ₹5,500 | frontier item matched by the owner's close-up |
| Foam mattress, double (under bedsheet) | 1 | ₹4,599 | ₹2,989 | frontier | – | ₹4,599 | – |  |
| Uppercase hard-shell trolley suitcase with printed cover | 1 | ₹3,499 | ₹1,166 | frontier | – | ₹3,499 | ₹2,500 | merged on 'possibly the same' (1.34) as mutual best match; low Jev confidence on price (0.49) |
| bedspread | 1 | ₹2,344 | ₹938 | local | ₹2,344 | – | – |  |
| GeoDebt router | 1 | ₹1,999 | ₹1,299 | frontier | ₹2,749 | ₹1,999 | – | low Jev confidence on identity (0.26); low Jev confidence on price (0.28) |
| Wooden stool with turned legs | 1 | ₹1,799 | ₹180 | frontier | ₹610 | ₹1,799 | – |  |
| Razer DeathAdder Essential wired gaming mouse | 1 | ₹1,649 | ₹165 | frontier | ₹5,744 | ₹1,649 | – |  |
| Eyelet window curtains, brown palm-tree print (set of 2 panels) | 2 | ₹1,398 | ₹560 | frontier | ₹629 | ₹699 | – | low Jev confidence on price (0.41) |
| Laptop backpack, navy blue | 1 | ₹1,299 | ₹844 | frontier | ₹1,305 | ₹1,299 | – | low Jev confidence on price (0.31); owner: free or provided (the owner said so); may not be the owner's to |
| Footwear under the almirah | 2 | ₹1,200 | ₹480 | frontier | – | ₹600 | – |  |
| Stainless steel curtain rod with brackets | 2 | ₹1,200 | ₹780 | frontier | – | ₹600 | – | possible double count with Eyelet window curtains, brown palm-tree pri |
| Pillow with peach cover | 1 | ₹1,030 | ₹670 | local | ₹1,030 | ₹399 | – | low Jev confidence on price (0.17) |
| Dohar / AC blanket, white with grey print, folded | 1 | ₹899 | ₹584 | frontier | – | ₹899 | – |  |
| Double bedsheet, patchwork print (red, black, beige) | 1 | ₹799 | ₹519 | local | ₹799 | ₹499 | – | low Jev confidence on price (0.13) |
| pillow | 1 | ₹713 | ₹107 | local | ₹713 | – | – | possible double count with Pillow with peach cover (opus-16), Jev 0.83 |
| USB phone charger with braided cable | 1 | ₹699 | ₹454 | frontier | ₹346 | ₹699 | – | merged on 'possibly the same' (1.45) as mutual best match; low Jev confidence on price (0.42) |
| curtain | 1 | ₹629 | ₹94 | local | ₹629 | – | – | possible double count with Eyelet window curtains, brown palm-tree pri |
| curtain | 1 | ₹629 | ₹94 | local | ₹629 | – | – | possible double count with Eyelet window curtains, brown palm-tree pri |
| Extended gaming mouse pad, anime print | 1 | ₹599 | ₹240 | frontier | – | ₹599 | – |  |
| tube light | 1 | ₹337 | ₹51 | local | ₹337 | – | – |  |
| Remote control, black (device unknown) | 1 | ₹299 | ₹194 | frontier | – | ₹299 | – |  |
| Wall-mounted light above the desk (bracket fitting) | 1 | ₹250 | ₹162 | frontier | – | ₹250 | – |  |
| Floor mop / broom | 1 | ₹199 | ₹80 | frontier | – | ₹199 | – |  |
| Roll-up whiteboard sheet on PVC pipes | 1 | ₹150 | ₹60 | voice | ₹1,139 | ₹450 | ₹150 | low Jev confidence on price (0.34) |
| LED bulb (yellow) in wall batten holder | 1 | ₹150 | ₹98 | frontier | – | ₹150 | – |  |
| **Building fixtures** | | | | | | | | |
| Window 1 (behind bed): wooden frame, glass casement shutters, MS decor | 1 | ₹38,000 | ₹15,200 | frontier | – | ₹38,000 | – |  |
| Window 2 (near door): wooden frame, glass shutters, MS grill | 1 | ₹30,400 | ₹12,160 | frontier | – | ₹30,400 | – |  |
| Panel door, natural teak-finish wood, with frame | 1 | ₹20,000 | ₹13,000 | frontier | – | ₹20,000 | – |  |
| Main door: flush door, orange laminate, with frame and lever lockset | 1 | ₹14,000 | ₹9,100 | frontier | – | ₹14,000 | – |  |
| PVC folding (accordion) door, beige | 1 | ₹5,500 | ₹3,575 | frontier | – | ₹5,500 | – |  |
| Extension board with universal sockets | 2 | ₹1,150 | ₹460 | frontier | ₹519 | ₹575 | – | merged on 'possibly the same' (1.42) as mutual best match; low Jev confidence on price (0.44) |
| Havells Eurobreaker MCB enclosure, 2 x SP B25 | 1 | ₹800 | ₹320 | frontier | – | ₹800 | – |  |
| Old wooden switchboard with bakelite round fittings (near window 2) | 1 | ₹800 | ₹120 | frontier | – | ₹800 | – |  |
| Switchboard near router (surface board) | 1 | ₹590 | ₹236 | local | ₹590 | ₹1,400 | – | possible double count with Old wooden switchboard with bakelite round  |
| Modular switchboard near the door | 1 | ₹209 | ₹84 | local | ₹209 | ₹700 | – | merged on 'possibly the same' (1.14) as mutual best match; possible double count with Switchboard near router (surface board) (op |
| switch | 1 | ₹144 | ₹22 | local | ₹144 | – | – | possible double count with Switchboard near router (surface board) (op |
| **Books** | | | | | | | | |
| Living nonviolent communication (Marshall B. Rosenberg) · self_help | 1 | ₹951 | ₹618 | local | ₹951 | ₹399 | – |  |
| A History of the World in 10 1/2 Chapters (Julian Barnes) · fiction | 1 | ₹799 | ₹320 | local | ₹799 | ₹499 | – |  |
| Annie May's Black Book (Debby Holt) · fiction | 1 | ₹695 | ₹278 | local | ₹695 | ₹499 | – | low Jev confidence on identity (0.39) |
| Iron Horse (Keith Miles) · mystery_thriller | 1 | ₹599 | ₹240 | frontier | – | ₹599 | – | merged on 'possibly the same' (1.46) as mutual best match |
| The Hare with Amber Eyes (author not read) · biography_memoir | 1 | ₹429 | ₹279 | local | ₹429 | ₹599 | – |  |
| unidentified book | 1 | ₹429 | ₹279 | local | ₹429 | – | – | possible double count with Torment (opus-36), Jev 1.49 |
| The 80/20 Principle (Richard Koch) · business_economics | 1 | ₹376 | ₹244 | frontier | ₹316 | ₹376 | – | low Jev confidence on identity (0.18); low Jev confidence on price (0.21) |
| The Great Gatsby (F. Scott Fitzgerald) · fiction | 1 | ₹350 | ₹140 | frontier | ₹154 | ₹350 | – | low Jev confidence on identity (0.38); low Jev confidence on price (0.08) |
| Antony and Cleopatra (William Shakespeare) · classics | 1 | ₹304 | ₹122 | local | ₹304 | ₹199 | – | low Jev confidence on price (0.30) |
| Torment (Lauren Kate) · fiction | 1 | ₹295 | ₹118 | local | ₹295 | ₹383 | – | low Jev confidence on identity (0.47); low Jev confidence on price (0.04) |
| Rock Paper Scissors (Alice Feeney) · mystery_thriller | 1 | ₹186 | ₹74 | frontier | ₹876 | ₹186 | – |  |
| The thread (Victoria Hislop) · fiction | 1 | ₹160 | ₹64 | local | ₹160 | ₹499 | – |  |

## Against the owner's ground truth

11/13 ground-truth items found; 4 with a recent purchase price, mean |RCV error| 10.0%

| Owner's item | Paid | Age (y) | Local | Frontier | Owner | Jev chose | RCV | Error |
|---|---|---|---|---|---|---|---|---|
| HP Victus gaming laptop (Ryzen 7 260, RTX 5050) | ₹190,000 | 0.08 | ₹77,245 | ₹76,021 | ₹190,000 | voice | ₹190,000 | +0.0% |
| Acer 24 inch monitor | ₹16,000 | 3 | ₹12,249 | ₹12,999 | – | local | ₹12,249 | – |
| chair | ₹5,500 | – | – | ₹8,499 | ₹5,500 | voice | ₹5,500 | – |
| L-shaped study table (desk) | ₹8,000 | 0.75 | ₹2,860 | ₹12,000 | ₹8,000 | voice | ₹8,000 | +0.0% |
| split AC | ₹35,000 | 1 | ₹32,900 | ₹35,890 | ₹35,000 | voice | ₹35,000 | +0.0% |
| bed | ₹450 | 35 | ₹19,190 | ₹17,989 | – | frontier | ₹17,989 | – |
| steel almirah | ₹350 | 40 | ₹7,999 | ₹18,100 | – | frontier | ₹18,100 | – |
| Razer DeathAdder mouse | ₹2,500 | 4 | ₹5,744 | ₹1,649 | – | frontier | ₹1,649 | – |
| suitcase | ₹2,500 | 2 | – | ₹3,499 | ₹2,500 | frontier | ₹3,499 | +40.0% |
| stool | ₹600 | 8 | ₹610 | ₹1,799 | – | frontier | ₹1,799 | – |
| whiteboard sheet | ₹150 | – | – | – | – | – | – | not found |
| JioFiber router | – | – | ₹2,749 | ₹1,999 | – | frontier | ₹1,999 | – |
| Good Knight liquid mosquito repellent | – | – | – | – | – | – | – | not found |

Error is only computed where the purchase is within 2 years, so the price paid is a fair replacement cost.

## How the sources ranked (Jev)

| Source | Items found | Found alone | Identity chosen | Price chosen |
|---|---|---|---|---|
| local | 40 | 8 | 3/32 | 12/28 |
| frontier | 47 | 15 | 28/32 | 13/30 |
| voice | 14 | 0 | 1/14 | 5/6 |
