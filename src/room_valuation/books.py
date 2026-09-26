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


STOP = {"the", "and", "of", "a", "an", "in", "on", "to", "for", "with", "by"}


def title_coverage(title: str, read: str) -> float:
    """Share of the title's words found in the text read off the spine, allowing one OCR slip
    and words run together (ROCKPAPERSCISSORS)."""
    words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in STOP]
    if not words:
        return 0.0
    read_words = re.findall(r"[a-z0-9]+", read.lower())
    compact = "".join(read_words)

    def found(w):
        return w in read_words or (len(w) >= 4 and w in compact) or any(
            difflib.SequenceMatcher(None, w, r).ratio() >= 0.8 for r in read_words)

    return sum(found(w) for w in words) / len(words)


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
    # a spine is the book itself, not a summary or study guide of it
    derivative = re.compile(r"\b(summary|study guide|analysis|workbook|companion|sparknotes|notes on|cliffsnotes)\b", re.I)
    docs = [d for d in r.json().get("docs", []) if not derivative.search(d.get("title", "")) or derivative.search(query)]
    if not docs:
        return None
    q = query.lower()

    def sim(d):
        """Half string similarity, half title coverage: most of the catalogue title's words must
        be in what was read. Without coverage 'The Thread' matched 'The Slender Thread' and a
        spine reading only SHAKESPEARE matched Hamlet."""
        whole = difflib.SequenceMatcher(None, q, f"{d.get('title', '')} {' '.join(d.get('author_name') or [])}".lower()).ratio()
        return 0.5 * whole + 0.5 * title_coverage(d.get("title", ""), q)

    best = max(docs, key=sim)
    isbns = best.get("isbn") or []
    isbn13 = next((i for i in isbns if len(i) == 13), isbns[0] if isbns else None)
    subjects = (best.get("subject") or [])[:12]
    return Book(title=best.get("title"), author=", ".join(best.get("author_name") or []) or None, isbn=isbn13,
                subjects=subjects, genre=rule_genre(subjects), lookup="openlibrary", match=round(sim(best), 2))
