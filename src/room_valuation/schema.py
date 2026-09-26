"""The one item shape every source reports in, so Jev can compare like with like."""

import json
import re

from pydantic import BaseModel, Field

RECENT_YEARS = 2  # a price paid is a replacement cost only when the purchase is this recent


def number(v) -> float | None:
    """A float out of a model answer: 1200, "1200", "Rs 1,200"; None for empty or unreadable."""
    if v in (None, "", "null"):
        return None
    try:
        return float(re.sub(r"[^\d.]", "", v) if isinstance(v, str) else v)
    except (TypeError, ValueError):
        return None


def json_object(text: str) -> dict:
    """The first {...} in a model reply, or {} when there is none or it does not parse."""
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}
    return d if isinstance(d, dict) else {}

CATEGORIES = [
    "laptop", "monitor", "computer_accessory", "phone", "audio", "networking",
    "appliance", "lighting", "electrical_fixture", "building_fixture", "furniture", "bedding",
    "book", "decor", "kitchenware", "bag_clothing", "other",
]

# insured under the building (dwelling) cover, not contents: reported as a separate total
BUILDING = {"electrical_fixture", "building_fixture"}

GENRES = [
    "fiction", "mystery_thriller", "science_fiction_fantasy", "romance", "classics",
    "biography_memoir", "self_help", "business_economics", "history", "philosophy",
    "religion_spirituality", "science", "computing_technology", "engineering_textbook",
    "mathematics", "poetry", "children", "comics_graphic", "reference", "other",
]


class Book(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    genre: str | None = None
    subjects: list[str] = Field(default_factory=list)
    lookup: str | None = None  # where title/isbn came from, e.g. "openlibrary"
    match: float | None = None  # similarity of the spine text to the catalogue record, 0..1


class Item(BaseModel):
    id: str
    source: str  # "local", "opus" or "astra", "voice"
    category: str
    name: str
    brand: str | None = None
    model: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    quantity: int = 1
    condition: str | None = None
    evidence: str | None = None  # text read off the item, or the spoken sentence
    photos: list[str] = Field(default_factory=list)
    regions: list[dict] = Field(default_factory=list)  # [{photo, box}] where it was seen
    book: Book | None = None
    rcv_inr: float | None = None  # replacement cost new, per unit
    price_source: str | None = None  # URL, price list entry id, or "said by owner"
    price_note: str | None = None
    age_years: float | None = None
    price_paid_inr: float | None = None
    link: str | None = None  # a voice note recorded on an item's page is about that item

    def describe(self) -> dict:
        """Compact text form for Jev: only fields that carry meaning."""
        d = {"category": self.category, "name": self.name}
        for key in ("brand", "model", "condition", "evidence"):
            if getattr(self, key):
                d[key] = getattr(self, key)
        if self.attributes:
            d["attributes"] = self.attributes
        if self.quantity != 1:
            d["quantity"] = str(self.quantity)
        if self.book and self.book.title:
            d["book"] = {k: v for k, v in self.book.model_dump().items() if v and k != "lookup"}
        return d


class SourceResult(BaseModel):
    source: str
    items: list[Item]
    room_area_m2: float | None = None
    shelves: int | None = None
    notes: list[str] = Field(default_factory=list)
    seconds: float | None = None
