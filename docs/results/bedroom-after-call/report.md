# Bedroom, Rourkela: contents valuation

Capture `20260927-061610-8b4353`, merged from 20260926-090044-d552ae
- Photos: 38 (room photos and video frames used for detection)
- Owner review: 28 items kept, 46 removed, 4 added, 12 close-ups, 12 voice notes
- Pipeline 2: claude-opus-5-5; Jev scored 108 pairs (similarity filter skipped 285)
- Market prices after Jev: 0 items searched on Serper, 0 priced, 0 unreadable books at the room median
- 3D: 38 photos and frames in 2 VGGT chunks, metric scale 2.0 (MoGe-2)
- Listings Jev judged: 41 this exact product, 132 similar, 128 different

## Totals

| | Replacement (RCV) | After depreciation (ACV) | Items |
|---|---|---|---|
| Contents (incl. books) | ₹248,480 | ₹202,968 | 39 |
| Building fixtures | ₹79,099 | ₹35,867 | 11 |
| **Total** | **₹327,579** | **₹238,835** | 50 |
| Held for review, not in the total | ₹3,214 to ₹53,413 | | 5 lines |

Books: 12, ₹5,910. Lines flagged for review: 30. Possible double counts: ₹1,079. Owner's review: 0 removed, 0 marked duplicate.

## Floor

**15.61 m² (168 sq ft)**, from tape measurement of this bedroom (floor plan take-home ground truth, 2026-09-20); 426.7 x 365.8 cm, ceiling 312.4 cm

- also 15.68 m² from floor plan pipeline, depth tier (20260920-035737-0c6f2b)
- also 15.0 m² from frontier model estimate from photos

![floor plan](floor_plan.png)

## Items

Price candidates: Local (pipeline 1's Serper search, repriced from the listings Jev judged this product or similar), Frontier (the frontier model's web price, room pass), Per object (the frontier model given every photo of this one object), Market (a second search after Jev, for what was still unpriced). Owner: what the owner said they paid; evidence to check, not a candidate. Price from: the one Jev trusted. Kind: exact (this model) or closest (the nearest similar product), with the 25th to 75th percentile of its listings.

| Item | Qty | RCV | Kind and range | ACV | Price from | Local | Frontier | Per object | Owner | Market | Flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Contents** | | | | | | | | | | | |
| HP Victus 15 gaming laptop 15-fb3185AX (Ryzen 7 260, RTX 5050 8GB, 24G | 1 | ₹131,999 | exact | ₹129,359 | object | ₹84,995 | ₹74,129 | ₹131,999 | ₹190,000 | – | frontier item matched by the owner's close-up; the owner says Rs 190,000, 44% above the market price: ask for a recei |
| Carrier split air conditioner (wall-mounted inverter indoor unit) | 1 | ₹35,490 | closest | ₹31,054 | object | ₹34,990 | ₹35,890 | ₹35,490 | ₹35,000 | – | frontier item matched by the owner's close-up; exact model not seen: priced as the closest equivalent; a close-up of  |
| wardrobe | 1 | ₹18,100 | held: – to ₹18,100 | ₹11,765 | object | – | – | ₹18,100 | – | – | low Jev confidence on identity (0.44); 3D size check: the object source's product is 180x90x50 cm against abo |
| two-door steel almirah (cupboard), pale green | 1 | ₹12,500 | closest | ₹3,125 | object | ₹19,949 | ₹18,100 | ₹12,500 | ₹500 | – | low Jev confidence on identity (0.45); low Jev confidence on price (0.49) |
| box bed with storage, no headboard, wood-grain laminate (diwan style) | 1 | ₹12,000 | closest | ₹3,000 | object | ₹26,499 | ₹14,000 | ₹12,000 | ₹300 | – | merged on 'possibly the same' (1.49) as mutual best match; 3D size check: the frontier source's product is 183x137 cm against abo |
| Acer ZeroFrame desktop monitor, about 24 inch, thin black bezel, round | 1 | ₹9,999 | closest | ₹5,000 | object | ₹6,558 | ₹12,999 | ₹9,999 | ₹16,000 | – | low Jev confidence on identity (0.40); exact model not seen: priced as the closest equivalent; a close-up of  |
| L-shaped computer desk, black laminated top on black square-tube steel | 1 | ₹9,000 | closest | ₹8,438 | object | ₹9,300 | ₹8,999 | ₹9,000 | ₹8,000 | – | frontier item matched by the owner's close-up; 3D size check: the object source's product is 150x150x75 cm against ab |
| Green Soul high-back mesh ergonomic office chair (probably Jupiter Sup | 1 | ₹8,690 | closest | ₹5,648 | object | ₹8,690 | ₹8,990 | ₹8,690 | ₹5,500 | – | frontier item matched by the owner's close-up; low Jev confidence on identity (0.42) |
| Mattress (under the bedsheet) | 1 | ₹6,000 | estimate | ₹3,900 | frontier | – | ₹6,000 | – | – | – |  |
| Wi-Fi router (wall-mounted, dark navy, brand not readable) | 1 | ₹3,729 | closest | ₹2,424 | object | ₹1,671 | ₹2,500 | ₹3,729 | – | – | merged on 'possibly the same' (1.20) as mutual best match; low Jev confidence on identity (0.30) |
| Navy blue laptop backpack, about 30 L, padded mesh back panel | 1 | ₹2,400 | closest | ₹1,560 | object | ₹774 | ₹1,200 | ₹2,400 | – | – | owner: free or provided (the owner said so); may not be the owner's to |
| Hard-shell spinner trolley suitcase, airport-signage print (LAX, Depar | 1 | ₹2,049 | held: ₹2,049 to ₹31,048 | ₹683 | object | ₹31,048 | ₹3,799 | ₹2,049 | ₹2,500 | – | merged on 'possibly the same' (1.49) as mutual best match; low Jev confidence on price (0.23) |
| Razer DeathAdder Essential wired gaming mouse (black) | 1 | ₹1,728 | closest | ₹346 | object | ₹1,699 | ₹1,749 | ₹1,728 | ₹2,500 | – | low Jev confidence on price (0.43); exact model not seen: priced as the closest equivalent; a close-up of  |
| Shoes under the almirah | 2 | ₹1,600 | estimate | ₹640 | frontier | – | ₹800 | – | – | – |  |
| wooden stool with turned legs | 1 | ₹1,500 | held: ₹387 to ₹1,500 | ₹375 | object | ₹387 | ₹1,500 | ₹1,500 | ₹600 | – | low Jev confidence on price (0.33); held for review: Jev is unsure (0.33) and the prices are 4 times apart |
| double bedsheet, patchwork geometric print (red, charcoal grey, beige, | 1 | ₹1,449 | held: ₹378 to ₹1,449 | ₹942 | object | ₹378 | ₹800 | ₹1,449 | – | – | low Jev confidence on price (0.24); held for review: Jev is unsure (0.24) and the prices are 4 times apart |
| white USB wall charger (phone fast-charge adapter) with black cable | 1 | ₹999 | closest | ₹649 | object | – | ₹600 | ₹999 | – | – | merged on 'possibly the same' (1.14) as mutual best match; low Jev confidence on identity (0.49) |
| Eyelet window curtain set, 2 panels, brown satin-finish polyester with | 1 | ₹999 | closest | ₹649 | object | ₹884 | ₹450 | ₹999 | – | – | frontier item matched by the owner's close-up |
| Eyelet window curtain set, 5 ft, brown and black polyester satin, digi | 1 | ₹999 | closest | ₹649 | object | ₹899 | ₹600 | ₹999 | – | – | frontier item matched by the owner's close-up |
| Folded white printed dohar or light blanket | 1 | ₹900 | estimate | ₹585 | frontier | – | ₹900 | – | – | – |  |
| double bedsheet, patchwork stripe print (red, charcoal, cream, beige) | 1 | ₹699 | closest | ₹454 | object | ₹799 | – | ₹699 | – | – | low Jev confidence on price (0.22) |
| Extended gaming mouse pad, anime print | 1 | ₹499 | estimate | ₹324 | frontier | – | ₹499 | – | – | – | exact model not seen: priced as the closest equivalent; a close-up of  |
| Bed pillow (fibre-filled, standard size) with printed cotton cover | 1 | ₹450 | closest | ₹292 | object | ₹656 | ₹350 | ₹450 | – | – |  |
| Wall-mounted light above the desk | 1 | ₹400 | estimate | ₹260 | frontier | – | ₹400 | – | – | – |  |
| dark curtain panel (black or dark brown, likely polyester) | 1 | ₹350 | closest | ₹228 | object | ₹1,499 | – | ₹350 | – | – | low Jev confidence on identity (0.29) |
| tube light | 1 | ₹330 | closest ₹290 to ₹399 | ₹214 | local | ₹330 | – | – | – | – |  |
| Black remote control (second device) | 1 | ₹300 | estimate | ₹195 | frontier | – | ₹300 | – | – | – |  |
| Long-handled cleaning brush or floor wiper | 1 | ₹250 | estimate | ₹100 | frontier | – | ₹250 | – | – | – |  |
| Yellow LED bulb in wall batten holder | 1 | ₹150 | estimate | ₹98 | frontier | – | ₹150 | – | – | – |  |
| Godrej Good Knight Good Knight Flash liquid vaporiser (plug-in machine | 1 | ₹110 | exact | ₹72 | object | ₹186 | ₹110 | ₹110 | – | – | frontier item matched by the owner's close-up |
| **Building fixtures** | | | | | | | | | | | |
| Window above the bed: wooden frame, glass shutters, MS grill | 1 | ₹18,000 | estimate | ₹7,200 | frontier | – | ₹18,000 | – | – | – |  |
| Window on the AC wall: wooden frame, glass shutters, MS grill | 1 | ₹18,000 | estimate | ₹7,200 | frontier | – | ₹18,000 | – | – | – |  |
| Teak-finish panelled wooden door with frame | 1 | ₹16,000 | estimate | ₹10,400 | frontier | – | ₹16,000 | – | – | – |  |
| Flush door, orange laminate, with frame, lever handle and cylinder loc | 1 | ₹13,000 | closest | ₹5,200 | frontier | – | ₹13,000 | – | – | – |  |
| Painted door or shutter beside the AC (pink) | 1 | ₹10,000 | estimate | ₹4,000 | frontier | – | ₹10,000 | – | – | – |  |
| Havells (MCBs); the round fittings and the enclosure brand could not b | 1 | ₹1,050 | closest | ₹420 | object | – | ₹1,200 | ₹1,050 | – | – |  |
| surface-mounted non-modular switch board with 7 piano switches, one 3- | 1 | ₹700 | closest | ₹280 | object | ₹960 | ₹1,500 | ₹700 | – | – | low Jev confidence on identity (0.28) |
| modular switchboard (white plate, about 6 modules) | 1 | ₹650 | closest | ₹422 | object | ₹1,059 | – | ₹650 | – | – | possible double count with Surface switchboard beside the router (whit; possible double count with Old wooden switchboard with round Bakelite  |
| Old wooden switchboard with round Bakelite fittings | 1 | ₹600 | estimate | ₹180 | frontier | – | ₹600 | – | – | – |  |
| 3-socket extension board with master switch | 1 | ₹599 | closest | ₹240 | object | ₹432 | ₹450 | ₹599 | – | – |  |
| Flexible vinyl whiteboard sheet (dry-erase), hung on two white PVC rod | 1 | ₹500 | held: ₹400 to ₹1,316 | ₹200 | object | ₹1,316 | ₹400 | ₹500 | ₹150 | – | merged on 'possibly the same' (1.00) as mutual best match; low Jev confidence on price (0.49) |
| Modular switchboard beside the second window | 1 | ₹500 | estimate | ₹325 | frontier | – | ₹500 | – | – | – |  |
| **Books** | | | | | | | | | | | |
| Rock Paper Scissors (Alice Feeney) · mystery_thriller | 1 | ₹1,002 | exact ₹411 to ₹2,303 | ₹651 | local | ₹1,002 | ₹350 | – | – | – |  |
| Living nonviolent communication (Marshall B. Rosenberg) · self_help | 1 | ₹836 | exact ₹427 to ₹1,636 | ₹543 | local | ₹836 | ₹450 | – | – | – | low Jev confidence on price (0.19) |
| Iron Horse (Keith Miles) · mystery_thriller | 1 | ₹699 | estimate | ₹350 | frontier | ₹234 | ₹699 | – | – | – | merged on 'possibly the same' (1.18) as mutual best match; low Jev confidence on price (0.38) |
| Annie May's Bluck Book (author not read) · other | 1 | ₹650 | closest | ₹422 | frontier | ₹429 | ₹650 | – | – | – |  |
| The Hare with Amber Eyes (author not read) · biography_memoir | 1 | ₹444 | exact ₹347 to ₹17,045 | ₹289 | local | ₹444 | ₹699 | – | – | – |  |
| A History of the World in 10 1/2 Chapters (Julian Barnes) · fiction | 1 | ₹433 | exact ₹325 to ₹616 | ₹281 | local | ₹433 | ₹499 | – | – | – |  |
| unidentified book | 1 | ₹429 | – | ₹279 | local | ₹429 | – | – | – | – | possible double count with Rock Paper Scissors (opus-41), Jev 1.19 |
| The 80/20 Principle (Richard Koch) · self_help | 1 | ₹406 | exact ₹273 to ₹672 | ₹264 | local | ₹406 | ₹550 | – | – | – | low Jev confidence on identity (0.29) |
| Torment (Lauren Kate) · science_fiction_fantasy | 1 | ₹383 | exact | ₹249 | frontier | ₹329 | ₹383 | – | – | – | low Jev confidence on identity (0.06); low Jev confidence on price (0.37) |
| Antony and Cleopatra (William Shakespeare) · classics | 1 | ₹246 | exact ₹184 to ₹294 | ₹160 | local | ₹246 | ₹250 | – | – | – |  |
| The thread (Victoria Hislop) · fiction | 1 | ₹210 | exact | ₹105 | local | ₹210 | ₹499 | – | – | – |  |
| The Great Gatsby (F. Scott Fitzgerald) · fiction | 1 | ₹172 | exact ₹146 to ₹198 | ₹112 | local | ₹172 | ₹350 | – | – | – | low Jev confidence on identity (0.49) |

## Against the owner's ground truth

13/13 ground-truth items found; 4 with a recent purchase price, mean |RCV error| 15.6%

| Owner's item | Paid | Age (y) | Local | Frontier | Per object | Owner | Chosen | RCV | Error |
|---|---|---|---|---|---|---|---|---|---|
| HP Victus gaming laptop (Ryzen 7 260, RTX 5050) | ₹190,000 | 0.08 | ₹84,995 | ₹74,129 | ₹131,999 | ₹190,000 | object | ₹131,999 | -30.5% |
| Acer 24 inch monitor | ₹16,000 | 3 | ₹6,558 | ₹12,999 | ₹9,999 | – | object | ₹9,999 | – |
| chair | ₹5,500 | – | ₹8,690 | ₹8,990 | ₹8,690 | ₹5,500 | object | ₹8,690 | – |
| L-shaped study table (desk) | ₹8,000 | 0.75 | ₹9,300 | ₹8,999 | ₹9,000 | ₹8,000 | object | ₹9,000 | +12.5% |
| split AC | ₹35,000 | 1 | ₹34,990 | ₹35,890 | ₹35,490 | ₹35,000 | object | ₹35,490 | +1.4% |
| bed | ₹450 | 35 | ₹26,499 | ₹14,000 | ₹12,000 | – | object | ₹12,000 | – |
| steel almirah | ₹350 | 40 | ₹19,949 | ₹18,100 | ₹12,500 | – | object | ₹12,500 | – |
| Razer DeathAdder mouse | ₹2,500 | 4 | ₹1,699 | ₹1,749 | ₹1,728 | – | object | ₹1,728 | – |
| suitcase | ₹2,500 | 2 | ₹31,048 | ₹3,799 | ₹2,049 | ₹2,500 | object | ₹2,049 | -18.0% |
| stool | ₹600 | 8 | ₹387 | ₹1,500 | ₹1,500 | – | object | ₹1,500 | – |
| whiteboard sheet | ₹150 | – | ₹1,316 | ₹400 | ₹500 | ₹150 | object | ₹500 | – |
| JioFiber router | – | – | ₹1,671 | ₹2,500 | ₹3,729 | – | object | ₹3,729 | – |
| Good Knight liquid mosquito repellent | – | – | ₹186 | ₹110 | ₹110 | – | object | ₹110 | – |

Error is only computed where the purchase is within 2 years, so the price paid is a fair replacement cost.

## How the sources ranked (Jev)

| Source | Items found | Found alone | Identity chosen | Price chosen |
|---|---|---|---|---|
| local | 39 | 2 | 5/37 | 8/34 |
| frontier | 48 | 15 | 7/33 | 3/33 |
| object | 26 | 0 | 25/26 | 25/25 |
| voice | 14 | 0 | 0/14 | 0/0 |
| market | 0 | 0 | 0/0 | 0/0 |
