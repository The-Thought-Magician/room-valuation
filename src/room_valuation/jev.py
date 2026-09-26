"""Jev combines the three sources: which items are the same object, which description and
which price to trust, what condition it is in, which genre a book is.

Jev only makes judgments. Following its docs, everything countable or numeric stays in
code: matching is greedy over Jev's probabilities, prices are chosen from candidates (never
computed by Jev), totals and depreciation are arithmetic in valuation.py.
"""

import os
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
}


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


def align(sources: list[list[Item]]) -> tuple[list[Group], list[dict]]:
    """One Score per plausible cross-source pair (same category, or either side 'other')."""
    flat = [it for items in sources for it in items]
    pairs = [(a, b) for i, a in enumerate(flat) for b in flat[i + 1 :]
             if _src(a) != _src(b) and (a.category == b.category or "other" in (a.category, b.category))]
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
        scored.append({"a": a.id, "b": b.id, "p_same": float(ans.probabilities.get("2", 0.0)),
                       "p_maybe": float(ans.probabilities.get("1", 0.0)), "score": ans.score,
                       "confidence": ans.confidence})

    by_id = {it.id: it for it in flat}
    group_of: dict[str, Group] = {}
    groups: list[Group] = []
    for it in flat:
        g = Group(members={_src(it): it})
        groups.append(g)
        group_of[it.id] = g
    # greedy: most certain pairs first, each group holds at most one item per source
    for s in sorted(scored, key=lambda s: -s["p_same"]):
        ga, gb = group_of[s["a"]], group_of[s["b"]]
        if ga is gb:
            continue
        if round(s["score"]) == 2 and not set(ga.members) & set(gb.members):
            ga.members.update(gb.members)
            ga.flags += gb.flags
            for it in gb.members.values():
                group_of[it.id] = ga
            groups.remove(gb)
        elif round(s["score"]) == 1:
            ga.flags.append(f"possibly the same as {by_id[s['b']].name} ({s['b']})")
    return groups, scored


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
                                          "this exact object new in India today?"},
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
