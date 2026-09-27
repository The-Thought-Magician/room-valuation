"""The configuration of an electronic item, read out of any text about it: OCR of a close-up
(a palm-rest sticker, the bottom label, the box, a Settings > About screen), the frontier
model's evidence, or the owner's words.

A laptop's price depends on its configuration more than its name: the HP Victus 15 sells from
about Rs 55k with an RTX 3050 to over Rs 1.5 lakh with an RTX 5060. Pricing "HP Victus 15"
takes the cheap end. The spec goes into the search (prices.query_for) and into what Jev
judges listings against, so a listing with another GPU is a similar product, not this one.

Rules, not a model: a small VLM invents specs (it gave the laptop "1440 x 900" and 14 inch).
"""

import re

CPU = [
    r"\b(?:amd\s+)?ryzen\s*(?:ai\s*)?[3579]\s*(?:pro\s*)?\d{3,4}[a-z]{0,3}\b",   # Ryzen 7 260, Ryzen 5 7535HS
    r"\b(?:amd\s+)?ryzen\s*[3579]\b",                                             # a sticker: RYZEN 7
    r"\b(?:intel\s+)?core\s*(?:ultra\s*)?[3579][\s-]*\d{3,5}[a-z]{0,2}\b",        # Core i7-13620H, Core Ultra 7 155H
    r"\b(?:intel\s+)?core\s*i[3579][\s-]*\d{4,5}[a-z]{0,2}\b",
    r"\bi[3579]-\d{4,5}[a-z]{0,2}\b",
    r"\b(?:intel\s+)?core\s*(?:ultra\s*)?i?[3579]\b",
    r"\bapple\s+m[1-5](?:\s*(?:pro|max|ultra))?\b",
    r"\bsnapdragon\s*x\s*(?:elite|plus)?\b",
]
GPU = [
    r"\b(?:nvidia\s+)?(?:geforce\s+)?rtx\s*a?\d{4}(?:\s*ti)?\b",                 # RTX 5050, RTX 4060 Ti
    r"\b(?:nvidia\s+)?(?:geforce\s+)?gtx\s*\d{3,4}(?:\s*ti)?\b",
    r"\b(?:amd\s+)?radeon\s*(?:rx\s*)?\d{3,4}[a-z]{0,2}\b",
    r"\b(?:intel\s+)?arc\s*[ab]?\d{3}[a-z]?\b",
]
RAM = r"\b(4|8|12|16|18|24|32|36|48|64|96|128)\s*gb\b(?:\s*(?:ddr[45x]?|lpddr[45x]?|ram|memory|unified))"
RAM_LOOSE = r"\b(?:installed\s+)?(?:ram|memory)\s*[:\-]?\s*(4|8|12|16|18|24|32|36|48|64|96|128)(?:\.0)?\s*gb\b"
STORAGE = (r"\b(128|256|512|1024|2048)\s*gb\s*(?:pcie\s*|nvme\s*|m\.2\s*)*(?:ssd|storage|nvme)\b"
           r"|\b([124])\s*tb\s*(?:pcie\s*|nvme\s*)*(?:ssd|hdd|storage)?\b")
SCREEN = r"\b(1[0-9](?:\.\d)?|2[0-9](?:\.\d)?|3[0-9](?:\.\d)?)\s*(?:\"|”|-?\s?inch(?:es)?\b|in\b)"
REFRESH = r"\b(60|75|90|100|120|144|165|180|240|300|360)\s*hz\b"
RESOLUTION = (r"\b(" + "|".join(f"{w}\\s*[x×]\\s*{h}" for w, h in ((1280, 720), (1366, 768), (1920, 1080), (1920, 1200),
              (2560, 1440), (2560, 1600), (2880, 1800), (3840, 2160))) + r"|fhd\+?|qhd\+?|wqxga|uhd|4k)\b")


def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    return re.sub(r"(?i)^(amd|intel|nvidia)\s+", "", re.sub(r"(?i)\bgeforce\s+", "", s)).upper().replace("RYZEN", "Ryzen") \
        .replace("CORE", "Core").replace("ULTRA", "Ultra").replace("RADEON", "Radeon").replace("APPLE", "Apple") \
        .replace("Core I", "Core i")


def _first(patterns: list[str], text: str) -> str | None:
    for p in patterns:  # most specific first: 'Ryzen 7 260' before 'Ryzen 7'
        m = re.search(p, text, re.I)
        if m:
            return _clean(m.group(0))
    return None


def parse(text: str, category: str | None = None) -> dict[str, str]:
    """{cpu, gpu, ram, storage, screen, refresh, resolution}, only what the text states."""
    t = (text or "").replace("|", " ")
    out = {}
    if cpu := _first(CPU, t):
        out["cpu"] = cpu
    if gpu := _first(GPU, t):
        out["gpu"] = gpu
    m = re.search(RAM, t, re.I) or re.search(RAM_LOOSE, t, re.I)
    if m:
        out["ram"] = f"{m.group(1)} GB"
    m = re.search(STORAGE, t, re.I)
    if m:
        out["storage"] = f"{m.group(1)} GB SSD" if m.group(1) else f"{m.group(2)} TB"
    if category in (None, "laptop", "monitor", "phone"):
        m = re.search(SCREEN, t, re.I)
        if m:
            out["screen"] = f"{m.group(1)} inch"
    m = re.search(REFRESH, t, re.I)
    if m:
        out["refresh"] = f"{m.group(1)} Hz"
    m = re.search(RESOLUTION, t, re.I)
    if m:
        out["resolution"] = re.sub(r"\s*[x×]\s*", "x", m.group(1)).upper()
    return out


PRICE_KEYS = ("cpu", "gpu", "ram", "storage")  # what moves a computer's price; searched and must match


def search_words(spec: dict[str, str]) -> str:
    """The spec as search words, most price-defining first: 'Ryzen 7 260 RTX 5050 16 GB'."""
    return " ".join(spec[k] for k in ("cpu", "gpu", "ram", "storage") if spec.get(k))
