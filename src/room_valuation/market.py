"""After Jev: a live market price for every item still unpriced.

Pipeline 1 prices its own readings, the frontier model prices its own, and the owner may give a
recent price; Jev ranks those. What is left is an item no source priced (a local search found no
matching listing, the frontier model missed it, the owner said nothing). Those are searched once
more with the identity Jev settled on, which is usually a better query than the local reading.
The result joins the item as a "market" candidate. A spine nobody could read is priced at the
median of the room's identified books.
"""

from room_valuation import prices
from room_valuation.jev import Group
from room_valuation.prices import query_for
from room_valuation.schema import Item


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
