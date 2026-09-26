"""After Jev: a live market price for every item no source priced.

Jev first settles what each item is (the best of the local, frontier and owner readings).
Then every merged item that still has no replacement price (no frontier price, no recent owner
price) is searched once on Serper with that identity: "HP Victus 15 gaming laptop", not the
local model's misread "HP VICTUS 14 inches laptop". The result joins the item as a "market"
candidate. A spine nobody could read is priced at the median of the room's identified books.
"""

from room_valuation import prices
from room_valuation.jev import Group
from room_valuation.schema import Item


def query_for(item: Item) -> tuple[str, list[str]]:
    """Search text, and the words a listing title must contain (the brand)."""
    if item.category == "book" and item.book and item.book.title:
        return f"{item.book.title} {item.book.author or ''} paperback".strip(), []
    parts = [item.brand, item.model, item.attributes.get("size"), item.name]
    seen, words = set(), []
    for w in " ".join(p for p in parts if p).split():  # "Acer" + "Acer 24 inch monitor" says Acer once
        if w.lower() not in seen:
            seen.add(w.lower())
            words.append(w)
    name = " ".join(words)
    must = [item.brand.split()[0]] if item.brand else []
    return name, must


def _identity(g: Group, n: int, answers: dict) -> Item:
    choice = answers.get(f"id_{n}")
    src = choice.choice if choice is not None else None
    return g.members.get(src) or next(iter(g.members.values()))


def _unreadable(it: Item) -> bool:
    return it.category == "book" and it.name in ("unidentified book", "book (title not read)")


def fill_missing(groups: list[Group], answers: dict, log: list) -> dict:
    """Adds a "market" member to every group without a price. Returns counts for the report."""
    searched = priced = 0
    unread = []
    for n, g in enumerate(groups):
        if any(it.rcv_inr for it in g.members.values()):
            continue
        ident = _identity(g, n, answers)
        if _unreadable(ident):
            unread.append((n, g, ident))
            continue
        q, must = query_for(ident)
        searched += 1
        try:
            p = prices.price_item(q, ident.category, must)
        except Exception as e:  # one bad lookup costs one price, not the valuation
            p = {"query": q, "rcv_inr": None, "note": f"price lookup failed: {type(e).__name__}"}
        log.append({"group": n, "identity": ident.id, "price": p})
        if not p.get("rcv_inr"):
            continue
        priced += 1
        note = f"median of {p['matched']} matching listings for '{q}'" + (
            f" ({', '.join(p['sellers'])})" if p.get("sellers") else "")
        g.members["market"] = _market_item(n, ident, p["rcv_inr"], p.get("url"), note)
    known = sorted(it.rcv_inr for g in groups if not any(_unreadable(m) for m in g.members.values())
                   for it in g.members.values() if it.category == "book" and it.rcv_inr)
    for n, g, ident in unread:
        if known:
            g.members["market"] = _market_item(n, ident, known[len(known) // 2], None,
                                               f"median of the {len(known)} identified book prices in this room")
    return {"searched": searched, "priced": priced, "unreadable_books": len(unread)}


def _market_item(n: int, ident: Item, rcv: float, url: str | None, note: str) -> Item:
    return Item(id=f"market-{n}", source="market", category=ident.category, name=ident.name, brand=ident.brand,
                model=ident.model, attributes=ident.attributes, quantity=ident.quantity, book=ident.book,
                rcv_inr=rcv, price_source=url, price_note=note)
