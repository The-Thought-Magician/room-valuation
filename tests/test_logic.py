"""Logic that needs no GPU, no network and no API keys."""

from types import SimpleNamespace

from room_valuation import frontier, local, prices, valuation
from room_valuation.jev import Group
from room_valuation.schema import Book, Item


def item(i, src, cat, name, photo, box=(0.1, 0.1, 0.5, 0.5), **kw):
    return Item(id=f"{src}-{i}", source=src, category=cat, name=name, photos=[photo],
                regions=[{"photo": photo, "box": list(box)}], **kw)


def test_merge_same_object_across_photos():
    a = item(0, "local", "monitor", "computer monitor", "p1.jpg")
    b = item(1, "local", "monitor", "computer monitor", "p2.jpg", brand="Acer")
    merged = local._merge([a, b])
    assert len(merged) == 1 and merged[0].photos == ["p1.jpg", "p2.jpg"] and merged[0].brand == "Acer"


def test_two_boxes_in_one_photo_stay_two_objects_unless_nested():
    a = item(0, "local", "bedding", "pillow", "p1.jpg", box=(0.0, 0.0, 0.2, 0.2))
    b = item(1, "local", "bedding", "pillow", "p1.jpg", box=(0.5, 0.5, 0.7, 0.7))
    assert len(local._merge([a, b])) == 2
    outer = item(2, "local", "monitor", "monitor", "p1.jpg", box=(0.0, 0.0, 0.6, 0.6))
    inner = item(3, "local", "monitor", "monitor", "p1.jpg", box=(0.1, 0.1, 0.5, 0.5))
    assert len(local._merge([outer, inner])) == 1


def test_placeholder_text_is_dropped():
    assert local._null("brand if a logo or name is readable, else null") is None
    assert local._null("none") is None
    assert local._null("Acer") == "Acer"


def test_acv_uses_age_then_condition_with_salvage_floor():
    v, basis = prices.acv(100000, "laptop", 1, None)  # 1 of 5 years used
    assert v == 80000 and "age 1" in basis
    v, _ = prices.acv(100000, "laptop", 20, None)  # past its life, floor at 10 percent
    assert v == 10000
    v, basis = prices.acv(10000, "furniture", None, "fair")
    assert v == 4000 and "condition" in basis


def test_price_match_filters_and_takes_median(monkeypatch):
    listings = [
        {"title": "Acer 27 inch FHD IPS monitor", "price": 12000, "seller": "Amazon.in", "url": "a"},
        {"title": "Acer 27 inch QHD IPS monitor", "price": 16000, "seller": "Flipkart", "url": "b"},
        {"title": "Acer 27 inch monitor 165Hz", "price": 18000, "seller": "Croma", "url": "c"},
        {"title": "HDMI cable 2 m", "price": 300, "seller": "Amazon.in", "url": "d"},
    ]
    monkeypatch.setattr(prices, "shopping", lambda q: listings)
    monkeypatch.setattr(prices, "quick_commerce", lambda q: [])
    p = prices.price_item("Acer 27 inch monitor", "monitor", ["Acer"])
    assert p["rcv_inr"] == 16000 and p["matched"] == 3 and p["url"] == "b"


def test_rupee_parsing():
    assert prices._rupees("now ₹16,499 was Rs. 21,000") == [16499.0, 21000.0]


def test_frontier_json_with_fence_and_prose():
    text = ('Here it is:\n```json\n{"items": [{"category": "book", "name": "Atomic Habits", '
            '"book": {"title": "Atomic Habits", "author": "James Clear", "genre": "self_help"}, '
            '"rcv_inr": "Rs 499", "quantity": 1}], "room_area_m2": 15.6}\n```')
    res = frontier._to_result(frontier._parse(text), "opus", 1.0)
    assert res.items[0].book.genre == "self_help" and res.items[0].rcv_inr == 499 and res.room_area_m2 == 15.6


def answer(choice=None, probs=None, conf=0.9, score=None):
    return SimpleNamespace(choice=choice, probabilities=probs or {}, confidence=conf, score=score)


def test_line_items_follow_jev_choices_and_add_up():
    local_i = Item(id="local-0", source="local", category="laptop", name="laptop", rcv_inr=60000, condition="good")
    opus_i = Item(id="opus-0", source="opus", category="laptop", name="HP Victus gaming laptop", brand="HP", rcv_inr=95000)
    voice_i = Item(id="voice-0", source="voice", category="laptop", name="HP Victus", rcv_inr=190000, age_years=1)
    book = Item(id="opus-1", source="opus", category="book", name="Atomic Habits", rcv_inr=499,
                book=Book(title="Atomic Habits", author="James Clear"))
    groups = [Group(members={"local": local_i, "frontier": opus_i, "voice": voice_i}), Group(members={"frontier": book})]
    answers = {
        "id_0": answer("frontier", {"local": 0.1, "frontier": 0.7, "voice": 0.2}),
        "price_0": answer("voice", {"local": 0.1, "frontier": 0.3, "voice": 0.6}, conf=0.4),
        "cond_0": answer(score=2.2),
        "genre_1": answer("self_help", {"self_help": 0.95}),
    }
    lines = valuation.line_items(groups, answers)
    lap = lines[0]
    assert lap["name"] == "HP Victus gaming laptop" and lap["rcv_inr"] == 190000
    assert lap["acv_inr"] == 152000  # 1 of 5 years used
    assert any("low Jev confidence on price" in f for f in lap["flags"])
    assert lines[1]["book"]["genre"] == "self_help"
    t = valuation.totals(lines)
    assert t["rcv_inr"] == 190499 and t["books"]["count"] == 1
    board = valuation.leaderboard(lines)
    assert board["voice"]["price"]["chosen"] == 1 and board["frontier"]["identity"]["chosen"] == 1


def test_similarity_filter_keeps_likely_pairs_and_drops_the_rest():
    from room_valuation import jev

    a = item(0, "local", "monitor", "computer monitor", "p1.jpg", brand="Acer")
    others = [item(i, "opus", "monitor", n, "p9.jpg") for i, n in
              enumerate(["Acer 27 inch monitor", "old CRT monitor", "tiny display", "photo frame screen", "tv"], 1)]
    others[0].brand = "Acer"
    pairs, skipped = jev.candidate_pairs([a, *others], k=3)
    ids = {b.id for _, b in pairs}
    assert "opus-1" in ids and len(pairs) <= 3 and skipped >= 2
    lamp = item(9, "opus", "lighting", "lamp", "p1.jpg")
    pairs, _ = jev.candidate_pairs([a, lamp])
    assert pairs == []  # different category never reaches Jev


def test_spine_bands_group_lines_by_row():
    from room_valuation import ocr

    lines = [{"text": "ATOMIC HABITS", "score": 0.99, "x0": 10, "y0": 0, "y1": 20},
             {"text": "James Clear", "score": 0.98, "x0": 300, "y0": 2, "y1": 18},
             {"text": "SAPIENS", "score": 0.97, "x0": 10, "y0": 40, "y1": 60}]
    bands = ocr._bands(lines)
    assert len(bands) == 2 and {ln["text"] for ln in bands[0]} == {"ATOMIC HABITS", "James Clear"}


def test_merge_rules_same_mutual_singleton_and_flag():
    from room_valuation import jev

    lap_l = Item(id="local-0", source="local", category="laptop", name="laptop")
    lap_o = Item(id="opus-0", source="opus", category="laptop", name="HP laptop")
    mon_l = Item(id="local-1", source="local", category="monitor", name="monitor")
    mon_o = Item(id="opus-1", source="opus", category="monitor", name="Acer monitor")
    ch_l = [Item(id=f"local-{i}", source="local", category="furniture", name="chair") for i in (2, 3)]
    ch_o = [Item(id=f"opus-{i}", source="opus", category="furniture", name="chair") for i in (2, 3)]
    flat = [lap_l, lap_o, mon_l, mon_o, *ch_l, *ch_o]
    scored = [
        {"a": "local-0", "b": "opus-0", "score": 0.46, "p_different": 0.55, "confidence": 0.31},  # singleton: merge
        {"a": "local-1", "b": "opus-1", "score": 1.8},  # Jev says same: merge
        {"a": "local-2", "b": "opus-2", "score": 1.1},  # mutual best: merge
        {"a": "local-3", "b": "opus-2", "score": 0.9},  # opus-2 already taken: flag
        {"a": "local-3", "b": "opus-3", "score": 0.3, "p_different": 0.8, "confidence": 0.7},  # different: apart
    ]
    groups = jev.merge(flat, scored)
    sizes = sorted(len(g.members) for g in groups)
    assert sizes == [1, 1, 2, 2, 2]
    flagged = [g for g in groups if any("possible double count" in f for f in g.flags)]
    assert len(flagged) == 1 and "local-3" in [it.id for it in flagged[0].members.values()]


def test_old_price_paid_is_not_a_replacement_price(monkeypatch):
    from room_valuation import voice

    class FakeVLM:
        def ask(self, *a, **k):
            return ('[{"category": "furniture", "name": "bed", "price_paid_inr": 500, "age_years": 35, "quote": "bed"},'
                    ' {"category": "appliance", "name": "AC", "price_paid_inr": 35000, "age_years": 1, "quote": "AC"}]')

    monkeypatch.setattr(voice.models, "VLM", FakeVLM)
    monkeypatch.setattr(voice.models, "free", lambda: None)
    bed, ac = voice.extract("...")
    assert bed.rcv_inr is None and bed.price_paid_inr == 500 and "too old" in bed.price_note
    assert ac.rcv_inr == 35000 and ac.age_years == 1


def test_building_fixtures_totalled_apart_from_contents():
    lines = [{"category": "electrical_fixture", "quantity": 1, "rcv_inr": 1200, "acv_inr": 600, "flags": [], "book": None},
             {"category": "building_fixture", "quantity": 1, "rcv_inr": 9000, "acv_inr": 6000, "flags": [], "book": None},
             {"category": "laptop", "quantity": 1, "rcv_inr": 190000, "acv_inr": 152000, "flags": [], "book": None}]
    t = valuation.totals(lines)
    assert t["contents"]["rcv_inr"] == 190000 and t["building_fixtures"]["rcv_inr"] == 10200 and t["rcv_inr"] == 200200


def test_voice_rules_read_prices_ages_and_free():
    from room_valuation import voice

    assert voice.parse_price("Acer, 24-inch, 16K, 3 years back.") == 16000
    assert voice.parse_price("it costed me 1.9 lakhs and it is one month old") == 190000
    assert voice.parse_price("purchased 2 years back for Rs.2500") == 2500
    assert voice.parse_price("Almera 500 rupees purchased 40 years back") == 500
    assert voice.parse_price("charger, it came with my phone") is None
    assert voice.parse_age("Acer, 24-inch, 16K, 3 years back.") == 3
    assert voice.parse_age("it is one month old") == 0.08
    assert voice.parse_age("And it was made 40 years back") == 40
    assert voice.parse_age("bought it last year") == 1
    assert voice.parse_age("It costed me about 150 rupees.") is None
    e = {"id": "local-30", "name": "router", "category": "networking", "quantity": 1}
    it = voice._item_claim({}, e, "It came for free and company provided it")
    assert it.rcv_inr is None and "free" in it.attributes["acquired"]
    mon = voice._item_claim({"brand": "Acer"}, {"id": "local-2", "name": "monitor", "category": "monitor"},
                            "Acer, 24-inch, 16K, 3 years back.")
    assert mon.rcv_inr is None and mon.price_paid_inr == 16000 and mon.age_years == 3


def test_spine_parsing_splits_loops_and_drops_fragments():
    q = local._vlm_spine_queries("Torment | Lauren Kate\nTurenate | Turenate | Turenate | Turenate\n"
                                 "The 80/20 Principle | Richard Koch | The Great Gatsby | F. Scott Fitzgerald\nNONE")
    assert q == ["Torment Lauren Kate", "Turenate", "The 80/20 Principle Richard Koch", "The Great Gatsby F. Scott Fitzgerald"]
    assert not local._plausible_spine("DOUBLEDAY")
    assert not local._plausible_spine("PICADOR XX")
    assert not local._plausible_spine("KATE")
    assert local._plausible_spine("Iron Horse Edward Marston")
    a, b = Book(title="The Great Gatsby"), Book(title="Great Gatsby")
    assert local._same_book(a, b)
    assert not local._same_book(Book(title="Torment"), Book(title="The Thread"))


def test_book_matching_handles_run_together_and_misread_titles():
    assert local._same_book(Book(title="Rock Paper Scissors", author="Alice Feeney"),
                            Book(title="ROCKPAPERSCISSORS FEENEY ALICE"))
    assert local._same_book(Book(title="Torment", author="Lauren Kate"), Book(title="Lauren Kate Forment"))
    assert not local._same_book(Book(title="Hamlet", author="William Shakespeare"),
                                Book(title="Antony and Cleopatra", author="William Shakespeare"))
    ocr_words = {"torment", "lauren", "kate", "ironhorse", "marston", "edward"}
    assert local._ocr_supports(Book(title="Iron Horse"), ocr_words | {"ironhorse"})
    assert not local._ocr_supports(Book(title="Anne of Green Gables"), ocr_words)


def test_typed_note_is_an_owner_claim():
    from room_valuation import voice

    e = {"id": "added-1", "name": "L-shaped study table", "category": "furniture", "quantity": 1,
         "note": "8k, 9 months old"}
    (it,) = voice.typed_notes([e], set())
    assert it.rcv_inr == 8000 and it.age_years == 0.75 and it.link == "added-1"
    assert voice.typed_notes([e], {"added-1"}) == []  # a voice note on the item wins


def test_title_coverage_rejects_near_miss_records():
    from room_valuation import books

    assert books.title_coverage("Rock Paper Scissors", "ROCKPAPERSCISSORS FEENEY ALICE") == 1.0
    assert books.title_coverage("The Slender Thread", "The Thread Victoria Hislop") < 0.6
    assert books.title_coverage("Hamlet", "SHAKESPEARE") == 0.0
    assert books.title_coverage("Torment", "Lauren Kate Forment") == 1.0


def test_unmatched_spines_become_unidentified_or_drop():
    matched = Item(id="b0", source="local", category="book", name="Nonviolent Communication",
                   book=Book(title="Nonviolent Communication", author="Marshall B. Rosenberg", lookup="openlibrary"))
    partial = Item(id="b1", source="local", category="book", name="NilINI COMMUNICATION",
                   book=Book(title="NilINI COMMUNICATION", lookup="spine text only"))
    stranger = Item(id="b2", source="local", category="book", name="Zorblax Quantum",
                    book=Book(title="Zorblax Quantum", lookup="spine text only"))
    card = Item(id="c", source="local", category="book", name="books")
    out = local._settle_books([matched, partial, stranger], "c", card)
    assert [o.name for o in out] == ["Nonviolent Communication", "unidentified book"]


def test_hallucinated_title_needs_half_its_words_in_the_ocr():
    ocr_words = {"annie", "black", "book", "torment", "lauren", "kate"}
    assert not local._ocr_supports(Book(title="Anne of Green Gables"), ocr_words)
    assert local._ocr_supports(Book(title="Annie May's Black Book"), ocr_words)


def test_blocking_pairs_run_together_book_titles():
    from room_valuation import jev

    a = Item(id="local-1", source="local", category="book", name="Ironhorse", book=Book(title="Ironhorse"))
    b = Item(id="opus-1", source="opus", category="book", name="Iron Horse", book=Book(title="Iron Horse"))
    c = Item(id="opus-2", source="opus", category="book", name="The Thread", book=Book(title="The Thread"))
    assert jev.similarity(a, b) > jev.similarity(a, c) + 0.3


def test_colocated_single_items_of_one_brand_merge_despite_jev():
    from room_valuation import jev

    a = Item(id="local-9", source="local", category="laptop", name="laptop", brand="HP", model="Vergence",
             photos=["f1.jpg", "f2.jpg"])
    b = Item(id="opus-0", source="opus", category="laptop", name="HP Victus 15", brand="HP", photos=["f2.jpg"])
    scored = [{"a": "local-9", "b": "opus-0", "score": 0.24, "p_different": 0.81, "confidence": 0.65}]
    groups = jev.merge([a, b], scored)
    assert len(groups) == 1 and any("Jev said different" in f for f in groups[0].flags)
