"""Spine text to a real book: Open Library search, best title match."""

import difflib
import re

import httpx

from room_valuation.schema import Book

GENRE_RULES = [  # subject keyword to genre, first hit wins
    ("science fiction", "science_fiction_fantasy"), ("fantasy", "science_fiction_fantasy"),
    ("mystery", "mystery_thriller"), ("thriller", "mystery_thriller"), ("detective", "mystery_thriller"),
    ("romance", "romance"), ("poetry", "poetry"), ("poems", "poetry"), ("biography", "biography_memoir"),
    ("memoir", "biography_memoir"), ("self-help", "self_help"), ("habit", "self_help"),
    ("success", "self_help"), ("business", "business_economics"), ("economics", "business_economics"),
    ("finance", "business_economics"), ("history", "history"), ("philosophy", "philosophy"),
    ("religion", "religion_spirituality"), ("spiritual", "religion_spirituality"),
    ("computer", "computing_technology"), ("programming", "computing_technology"),
    ("engineering", "engineering_textbook"), ("mathematics", "mathematics"), ("physics", "science"),
    ("science", "science"), ("juvenile", "children"), ("comic", "comics_graphic"),
    ("fiction", "fiction"),
]


def rule_genre(subjects: list[str]) -> str:
    text = " ".join(subjects).lower()
    for key, genre in GENRE_RULES:
        if key in text:
            return genre
    return "other"


def lookup(spine_text: str, timeout: float = 15.0) -> Book | None:
    """Search Open Library with the text read off a spine and keep the closest title."""
    query = re.sub(r"[^\w\s']", " ", spine_text).strip()
    if len(query) < 3:
        return None
    try:
        r = httpx.get("https://openlibrary.org/search.json", timeout=timeout,
                      params={"q": query, "limit": 5, "fields": "title,author_name,isbn,subject"})
        r.raise_for_status()
    except httpx.HTTPError:
        return None
    docs = r.json().get("docs", [])
    if not docs:
        return None
    q = query.lower()

    def sim(d):
        return difflib.SequenceMatcher(None, q, f"{d.get('title', '')} {' '.join(d.get('author_name') or [])}".lower()).ratio()

    best = max(docs, key=sim)
    isbns = best.get("isbn") or []
    isbn13 = next((i for i in isbns if len(i) == 13), isbns[0] if isbns else None)
    subjects = (best.get("subject") or [])[:12]
    return Book(title=best.get("title"), author=", ".join(best.get("author_name") or []) or None, isbn=isbn13,
                subjects=subjects, genre=rule_genre(subjects), lookup=f"openlibrary (match {sim(best):.2f})")
