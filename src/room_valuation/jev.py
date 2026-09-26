"""Jev combines the three sources: which items are the same object, which description and
which price to trust, what condition it is in, which genre a book is.

Jev only makes judgments. Following its docs, everything countable or numeric stays in
code: matching is greedy over Jev's probabilities, prices are chosen from candidates (never
computed by Jev), totals and depreciation are arithmetic in valuation.py.
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from typesafe_sdk import Choice, Score, TypeSafeClient

from room_valuation.schema import GENRES, Item

MODEL = os.environ.get("TYPESAFE_MODEL", "jev-latest")
BATCH = 40  # questions per request; one call per batch is cheaper than one per question
WORKERS = 6  # the public endpoint rate-limits above roughly eight concurrent calls
SAME_LEVELS = ["different objects", "possibly the same object, not sure", "the same physical object"]
CONDITION_LEVELS = ["poor", "fair", "good", "like_new"]
STATE = {
    "task": "Home contents inventory of one room in India for an insurance claim.",
    "sources": {
        "local": "small local vision models on the photos; reliable on what is there, weak on exact models",
        "frontier": "a large vision model with web search on the same photos",
        "voice": "the owner describing their things out loud; knows what they bought, may misremember prices",
    },
    "how_to_compare": "Sizes, models and prices read from photos are estimates and are often off by a few "
                      "inches or centimetres. Judge sameness by the kind of object, where it "
                      "was seen, colour and distinguishing details. The owner has no photos; match their words by "
                      "kind of object and brand.",
}
MERGE_SCORE = 1.5  # expected level >= 1.5: Jev leans to 'the same physical object'
MAYBE_SCORE = 0.75  # between this and MERGE_SCORE: 'possibly the same'
# one item of the category per source (one laptop, one laptop): the same object unless Jev is
# confident it is not
SINGLETON_BLOCK = {"p_different": 0.6, "confidence": 0.5}


@dataclass
class Group:
    members: dict[str, Item] = field(default_factory=dict)  # source -> item
    flags: list[str] = field(default_factory=list)


def _client() -> TypeSafeClient | None:
    return TypeSafeClient(model=MODEL, timeout=120.0) if os.environ.get("TYPESAFE_API_KEY") else None


def ask(questions: dict, state: dict | None = None) -> dict:
    """Send questions in batches, in parallel. Returns {question id: answer}."""
    client = _client()
    if client is None:
        raise RuntimeError("TYPESAFE_API_KEY not set")
    keys = list(questions)
    batches = [{k: questions[k] for k in keys[i : i + BATCH]} for i in range(0, len(keys), BATCH)]

    def call(batch):
        return client.system_one(state=state or STATE, questions=batch).answers

    answers = {}
    with ThreadPoolExecutor(WORKERS) as pool:
        for part in pool.map(call, batches):
            answers.update(part)
    return answers


def _src(item: Item) -> str:
    return "frontier" if item.source in ("opus", "astra") else item.source


def _view(item: Item) -> dict:
    d = item.describe()
    if item.photos:
        d["seen_in_photos"] = ", ".join(item.photos)
    return d


def _words(item: Item) -> set[str]:
    text = " ".join([item.name, item.brand or "", item.model or "", *item.attributes.values(),
                     item.book.title or "" if item.book else "", item.book.author or "" if item.book else ""])
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


def similarity(a: Item, b: Item) -> float:
    """Cheap blocking score: word overlap, plus a bonus when both were seen in the same photo."""
    wa, wb = _words(a), _words(b)
    jac = len(wa & wb) / len(wa | wb) if wa | wb else 0.0
    return jac + (0.3 if set(a.photos) & set(b.photos) else 0.0) + (0.2 if a.brand and b.brand
                                                                     and a.brand.lower() == b.brand.lower() else 0.0)


def candidate_pairs(flat: list[Item], k: int = 3, min_sim: float = 0.05) -> tuple[list[tuple[Item, Item]], int]:
    """Only pairs worth a Jev call: same category (or either 'other'), and among each item's k
    most similar items from each other source. Returns the pairs and how many were skipped."""
    allowed = [(a, b) for i, a in enumerate(flat) for b in flat[i + 1 :]
               if _src(a) != _src(b) and (a.category == b.category or "other" in (a.category, b.category))]
    best: dict[tuple[str, str], list[tuple[float, tuple[str, str]]]] = {}  # (item, other source) -> scored pairs
    for a, b in allowed:
        s, key = similarity(a, b), (a.id, b.id)
        if s >= min_sim or a.category == "book":
            best.setdefault((a.id, _src(b)), []).append((s, key))
            best.setdefault((b.id, _src(a)), []).append((s, key))
    keep = {key for scored in best.values() for _, key in sorted(scored, reverse=True)[:k]}
    pairs = [(a, b) for a, b in allowed if (a.id, b.id) in keep]
    return pairs, len(allowed) - len(pairs)


def align(sources: list[list[Item]]) -> tuple[list[Group], list[dict], int]:
    """One Score per candidate cross-source pair after the similarity filter."""
    flat = [it for items in sources for it in items]
    ids = {it.id for it in flat}
    linked = [it for it in flat if it.link in ids]  # voice notes recorded on an item's own page
    pairs, skipped = candidate_pairs([it for it in flat if it not in linked])
    questions = {
        f"pair_{n}": Score(
            instructions={"item_a": _view(a), "item_b": _view(b),
                          "question": "Do item_a and item_b describe the same physical object in this room?"},
            criteria=SAME_LEVELS,
        )
        for n, (a, b) in enumerate(pairs)
    }
    answers = ask(questions) if questions else {}
    scored = []
    for n, (a, b) in enumerate(pairs):
        ans = answers[f"pair_{n}"]
        probs = {int(k): float(v) for k, v in ans.probabilities.items()}
        scored.append({"a": a.id, "b": b.id, "p_same": probs.get(2, 0.0), "p_maybe": probs.get(1, 0.0),
                       "p_different": probs.get(0, 0.0), "score": float(ans.score), "confidence": float(ans.confidence)})
    return merge(flat, scored), scored, skipped


def merge(flat: list[Item], scored: list[dict]) -> list[Group]:
    groups = _merge_scored([it for it in flat if not it.link or it.link not in {x.id for x in flat}], scored)
    home = {it.id: g for g in groups for it in g.members.values()}
    for it in flat:
        if it.link and it.link in home:
            g = home[it.link]
            if _src(it) in g.members:
                g.flags.append(f"second voice note ignored: {it.evidence}")
            else:
                g.members[_src(it)] = it
    return groups


def _merge_scored(flat: list[Item], scored: list[dict]) -> list[Group]:
    """Groups from Jev's pair scores. Rules, applied most certain pair first; a group never
    holds two items from the same source:
    1. score >= MERGE_SCORE: Jev says the same object.
    2. score >= MAYBE_SCORE and each item is the other's best-scoring candidate: merged, flagged.
    3. both sources report exactly one item of this category (one laptop and one laptop) and
       Jev is not confident they differ: merged, flagged.
    Anything else at or above MAYBE_SCORE stays apart and is flagged as a possible double count."""
    by_id = {it.id: it for it in flat}
    best: dict[tuple[str, str], float] = {}  # (item, other source) -> best score
    for s in scored:
        for x, y in ((s["a"], s["b"]), (s["b"], s["a"])):
            key = (x, _src(by_id[y]))
            best[key] = max(best.get(key, 0.0), s["score"])
    per_cat: dict[tuple[str, str], int] = {}
    for it in flat:
        per_cat[(_src(it), it.category)] = per_cat.get((_src(it), it.category), 0) + 1

    group_of: dict[str, Group] = {}
    groups: list[Group] = []
    for it in flat:
        g = Group(members={_src(it): it})
        groups.append(g)
        group_of[it.id] = g
    for s in sorted(scored, key=lambda s: -s["score"]):
        a, b = by_id[s["a"]], by_id[s["b"]]
        ga, gb = group_of[a.id], group_of[b.id]
        if ga is gb:
            continue
        mutual = s["score"] >= best[(a.id, _src(b))] and s["score"] >= best[(b.id, _src(a))]
        singleton = a.category == b.category and per_cat[(_src(a), a.category)] == 1 == per_cat[(_src(b), b.category)]
        rule = None
        if s["score"] >= MERGE_SCORE:
            rule = ""
        elif s["score"] >= MAYBE_SCORE and mutual:
            rule = f"merged on 'possibly the same' ({s['score']:.2f}) as mutual best match"
        elif singleton and not (s.get("p_different", 0.0) >= SINGLETON_BLOCK["p_different"]
                                and s.get("confidence", 0.0) >= SINGLETON_BLOCK["confidence"]):
            rule = f"merged as the only {a.category} in both sources (Jev {s['score']:.2f})"
        if rule is not None and not set(ga.members) & set(gb.members):
            ga.members.update(gb.members)
            ga.flags += gb.flags + ([rule] if rule else [])
            for it in gb.members.values():
                group_of[it.id] = ga
            groups.remove(gb)
        elif s["score"] >= MAYBE_SCORE:
            ga.flags.append(f"possible double count with {b.name} ({b.id}), Jev {s['score']:.2f}")
    return groups


def rank_groups(groups: list[Group]) -> dict:
    """Per group: which description, which price, what condition; per book: which genre."""
    q = {}
    for n, g in enumerate(groups):
        if len(g.members) > 1:
            q[f"id_{n}"] = Choice(
                instructions={"descriptions": {s: _view(it) for s, it in g.members.items()},
                              "question": "These descriptions are of one object. Which one identifies it most "
                                          "specifically and correctly, given the text read off it and the owner's words?"},
                criteria={s: None for s in g.members},
            )
        cands = {s: it for s, it in g.members.items() if it.rcv_inr}
        if len(cands) > 1:
            q[f"price_{n}"] = Choice(
                instructions={"object": _view(next(iter(g.members.values()))),
                              "candidates": {s: {"price_inr": f"Rs {it.rcv_inr:,.0f}", "basis": _basis(it)}
                                             for s, it in cands.items()},
                              "question": "Which candidate is the most reliable estimate of what it costs to buy "
                                          "this exact object new in India today?",
                              "how_to_judge": "A price the owner paid within the last 12 months for this exact item "
                                              "is the strongest evidence. Next best is a listing for the same model. A "
                                              "listing for a similar item or a class estimate is weaker, and a web "
                                              "median over many different models is weakest."},
                criteria={s: None for s in cands},
            )
        conds = {s: it.condition for s, it in g.members.items() if it.condition}
        if conds:
            q[f"cond_{n}"] = Score(
                instructions={"condition_reports": conds, "question": "What condition is this object in?"},
                criteria=CONDITION_LEVELS,
            )
        book = next((it.book for it in g.members.values() if it.book and it.book.title), None)
        if book:
            q[f"genre_{n}"] = Choice(
                instructions={"book": {k: v for k, v in book.model_dump().items() if v and k in ("title", "author", "subjects")},
                              "question": "Which genre does this book belong to?"},
                criteria={gname: None for gname in GENRES},
            )
    return ask(q) if q else {}


def _basis(it: Item) -> str:
    if it.source == "voice":
        age = f", {it.age_years:g} years ago" if it.age_years is not None else ""
        return f"what the owner says they paid{age}"
    return " ".join(x for x in (it.price_note, it.price_source) if x) or "no basis given"
