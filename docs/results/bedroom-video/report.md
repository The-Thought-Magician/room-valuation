# Bedroom, India: contents valuation

Capture `20260926-080711-5034d5`
- Photos: 16 (room photos and video frames used for detection)
- Owner review: 21 items kept, 18 removed, 1 added, 1 close-ups, 0 voice notes
- Pipeline 2: claude-opus-5-5; Jev scored 101 pairs (similarity filter skipped 202)
- Market prices after Jev: 5 items searched on Serper, 4 priced, 1 unreadable books at the room median

## Totals

| | Replacement (RCV) | After depreciation (ACV) | Items |
|---|---|---|---|
| Contents (incl. books) | ₹336,328 | ₹255,052 | 43 |
| Building fixtures | ₹33,200 | ₹16,130 | 10 |
| **Total** | **₹369,528** | **₹271,182** | 53 |

Books: 14, ₹5,693. Lines flagged for review: 10. Possible double counts: ₹10,378. Owner's review: 0 removed, 0 marked duplicate.

## Floor

**15.61 m² (168 sq ft)**, from tape measurement of this bedroom (floor plan take-home ground truth, 2026-09-20); 426.7 x 365.8 cm, ceiling 312.4 cm

- also 15.68 m² from floor plan pipeline, depth tier (20260920-035737-0c6f2b)
- also 11.62 m² from floor plan pipeline, video tier
- also 12.0 m² from frontier model estimate from photos

![floor plan](floor_plan.png)

## Items

Price from: the frontier model's web price, the owner's recent price, or the market price searched after Jev for items no source priced. Jev chooses when more than one exists.

| Item | Qty | RCV | ACV | Price from | Frontier | Owner | Market | Flags |
|---|---|---|---|---|---|---|---|---|
| **Contents** | | | | | | | | |
| HP Victus 15 gaming laptop (AMD Ryzen, NVIDIA GeForce RTX) | 1 | ₹190,000 | ₹186,960 | voice | ₹78,990 | ₹190,000 | – | merged on 'possibly the same' (0.90) as mutual best match |
| Carrier split air conditioner (indoor unit, with remote) | 1 | ₹35,890 | ₹14,356 | frontier | ₹35,890 | – | – |  |
| wardrobe | 1 | ₹20,384 | ₹3,058 | market | – | – | ₹20,384 |  |
| Double bed with box storage | 1 | ₹18,000 | ₹11,700 | frontier | ₹18,000 | – | – |  |
| Acer 27 inch class monitor, thin bezel, red-accent stand | 1 | ₹11,589 | ₹4,636 | frontier | ₹11,589 | – | – |  |
| High-back mesh ergonomic office chair with headrest | 1 | ₹9,000 | ₹3,600 | frontier | ₹9,000 | – | – |  |
| Mattress (double/queen) | 1 | ₹9,000 | ₹5,850 | frontier | ₹9,000 | – | – |  |
| L-shaped computer desk, wenge engineered-wood top, black metal legs | 1 | ₹8,999 | ₹5,849 | frontier | ₹8,999 | – | – |  |
| L-shaped study table | 1 | ₹8,000 | ₹7,400 | voice | – | ₹8,000 | – | possible double count with L-shaped computer desk, wenge engineered-wo; low Jev confidence on identity (0.25) |
| Hard-shell trolley suitcase in printed stretch cover | 1 | ₹3,500 | ₹1,400 | frontier | ₹3,500 | – | – |  |
| Wall-mounted Wi-Fi router (ISP fibre type) | 1 | ₹2,500 | ₹1,625 | frontier | ₹2,500 | – | – |  |
| Razer DeathAdder Essential wired gaming mouse | 1 | ₹1,749 | ₹700 | frontier | ₹1,749 | – | – |  |
| Wooden stool with turned legs | 1 | ₹1,500 | ₹600 | frontier | ₹1,500 | – | – |  |
| Laptop backpack, navy/black | 1 | ₹1,500 | ₹600 | frontier | ₹1,500 | – | – | merged on 'possibly the same' (1.49) as mutual best match |
| pillow | 1 | ₹1,399 | ₹210 | market | – | – | ₹1,399 |  |
| Eyelet curtain panels, brown printed header with black body | 3 | ₹1,350 | ₹540 | frontier | ₹450 | – | – |  |
| White quilted comforter/dohar (folded) | 1 | ₹1,299 | ₹844 | frontier | ₹1,299 | – | – |  |
| Wall chargers / power adapters plugged into the extension board | 2 | ₹1,000 | ₹650 | frontier | ₹500 | – | – |  |
| Patchwork double bedsheet/bedcover (red, black, beige, white) | 1 | ₹899 | ₹584 | frontier | ₹899 | – | – |  |
| Stainless steel curtain rod with brackets | 1 | ₹700 | ₹455 | frontier | ₹700 | – | – |  |
| curtain | 1 | ₹629 | ₹94 | market | – | – | ₹629 | possible double count with Eyelet curtain panels, brown printed header |
| Extended printed gaming mouse pad | 1 | ₹599 | ₹240 | frontier | ₹599 | – | – |  |
| Black IR remote with sleep (moon) key, likely a BLDC ceiling fan remot | 1 | ₹400 | ₹260 | frontier | ₹400 | – | – |  |
| Wall-mounted planning chart / roll-up writing sheet with handwritten n | 1 | ₹300 | ₹120 | frontier | ₹300 | – | – |  |
| tube light | 1 | ₹299 | ₹45 | market | – | – | ₹299 |  |
| Bulb in wall batten holder near the ceiling (yellow) | 1 | ₹150 | ₹60 | frontier | ₹150 | – | – |  |
| **Building fixtures** | | | | | | | | |
| Main room door with frame and lever handle | 1 | ₹14,000 | ₹5,600 | frontier | ₹14,000 | – | – |  |
| Window behind the curtains, with frame, glass and grill | 1 | ₹12,000 | ₹7,800 | frontier | ₹12,000 | – | – |  |
| Small ventilator opening beside the AC | 1 | ₹2,500 | ₹1,000 | frontier | ₹2,500 | – | – |  |
| Switchboard 1: surface board by the router (desk wall) | 1 | ₹1,800 | ₹720 | frontier | ₹1,800 | – | – | merged on 'possibly the same' (1.23) as mutual best match |
| Power extension board with switches | 2 | ₹900 | ₹360 | frontier | ₹450 | – | – |  |
| Switchboard 3: modular plate by the door | 1 | ₹900 | ₹360 | frontier | ₹900 | – | – | merged on 'possibly the same' (1.29) as mutual best match; possible double count with Switchboard 1: surface board by the router  |
| Switchboard 2: old porcelain switches on a wooden base (window corner) | 1 | ₹600 | ₹90 | frontier | ₹600 | – | – |  |
| Small surface switch/junction boxes on the window-side wall | 2 | ₹500 | ₹200 | frontier | ₹250 | – | – |  |
| **Books** | | | | | | | | |
| Iron Horse (Edward Marston) · mystery_thriller | 1 | ₹699 | ₹280 | frontier | ₹699 | – | – |  |
| The Hare with Amber Eyes (author not read) · biography_memoir | 1 | ₹599 | ₹240 | frontier | ₹599 | – | – |  |
| Annte Moys Black Book (author not read) · fiction | 1 | ₹499 | ₹200 | frontier | ₹499 | – | – |  |
| A HISTORYOF THEWORLD IN 0CHAPTERS (author not read) · history | 1 | ₹499 | ₹200 | frontier | ₹499 | – | – |  |
| The 80/20 Principle (Richard Koch) · business_economics | 1 | ₹450 | ₹292 | frontier | ₹450 | – | – | low Jev confidence on identity (0.48) |
| The thread (Victoria Hislop) · fiction | 1 | ₹450 | ₹180 | frontier | ₹450 | – | – |  |
| NodeCOMMUNICATION MARSHALL B ROSENBERG (author not read) · self_help | 1 | ₹450 | ₹292 | frontier | ₹450 | – | – |  |
| unidentified book | 1 | ₹450 | ₹292 | market | – | – | ₹450 | possible double count with Nonviolent Communication (opus-32), Jev 1.8 |
| Rock Paper Scissors (Alice Feeney) · mystery_thriller | 1 | ₹399 | ₹160 | frontier | ₹399 | – | – |  |
| Dout yort (author not read) · other | 1 | ₹399 | ₹160 | frontier | ₹399 | – | – | possible double count with The Iron Horse (opus-34), Jev 0.91 |
| unknown (spine not visible) (unknown) · other | 1 | ₹350 | ₹140 | frontier | ₹350 | – | – |  |
| THE GREAT GATSBY  NO (author not read) · classics | 1 | ₹250 | ₹100 | frontier | ₹250 | – | – |  |
| Antony and Cleopatra (William Shakespeare) · classics | 1 | ₹199 | ₹80 | frontier | ₹199 | – | – |  |
| Ironhorse (Peter Lorie) · history | 1 | – | – | – | – | – | – | no price from any source |

## Against the owner's ground truth

10/13 ground-truth items found; 4 with a recent purchase price, mean |RCV error| 13.8%

| Owner's item | Paid | Age (y) | Frontier | Owner | Market | Chosen | RCV | Error |
|---|---|---|---|---|---|---|---|---|
| HP Victus gaming laptop (Ryzen 7 260, RTX 5050) | ₹190,000 | 0.08 | ₹78,990 | ₹190,000 | – | voice | ₹190,000 | +0.0% |
| Acer 24 inch monitor | ₹16,000 | 3 | ₹11,589 | – | – | frontier | ₹11,589 | – |
| chair | ₹5,500 | – | ₹9,000 | – | – | frontier | ₹9,000 | – |
| L-shaped study table (desk) | ₹8,000 | 0.75 | ₹8,999 | – | – | frontier | ₹8,999 | +12.5% |
| split AC | ₹35,000 | 1 | ₹35,890 | – | – | frontier | ₹35,890 | +2.5% |
| bed | ₹450 | 35 | ₹18,000 | – | – | frontier | ₹18,000 | – |
| steel almirah | ₹350 | 40 | – | – | – | – | – | not found |
| Razer DeathAdder mouse | ₹2,500 | 4 | ₹1,749 | – | – | frontier | ₹1,749 | – |
| suitcase | ₹2,500 | 2 | ₹3,500 | – | – | frontier | ₹3,500 | +40.0% |
| stool | ₹600 | 8 | ₹1,500 | – | – | frontier | ₹1,500 | – |
| whiteboard sheet | ₹150 | – | – | – | – | – | – | not found |
| JioFiber router | – | – | ₹2,500 | – | – | frontier | ₹2,500 | – |
| Good Knight liquid mosquito repellent | – | – | – | – | – | – | – | not found |

Error is only computed where the purchase is within 2 years, so the price paid is a fair replacement cost.

## How the sources ranked (Jev)

| Source | Items found | Found alone | Identity chosen | Price chosen |
|---|---|---|---|---|
| local | 32 | 1 | 4/26 | 0/0 |
| frontier | 41 | 16 | 22/25 | 0/1 |
| voice | 2 | 0 | 0/2 | 1/1 |
| market | 5 | 0 | 0/0 | 0/0 |
