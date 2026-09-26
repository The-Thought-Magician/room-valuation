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
