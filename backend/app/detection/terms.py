"""User-supplied terms and propagation of found values to every other occurrence."""
import re
import uuid

from .models import Finding, PageText
from .pages import rects_for
from .sensitivity import profile

MAX_TERMS = 50
MIN_TERM = 2
MAX_TERM = 100
NAME_PART_MIN = 3


def clean_terms(terms) -> list[str]:
    seen, out = set(), []
    for term in terms or []:
        value = " ".join(str(term).split())
        if MIN_TERM <= len(value) <= MAX_TERM and value.lower() not in seen:
            seen.add(value.lower())
            out.append(value)
    return out[:MAX_TERMS]


def _pattern(value: str) -> re.Pattern:
    """Case-insensitive, whitespace-flexible, whole-word (or whole-number) match of a literal value."""
    body = r"\s+".join(re.escape(part) for part in value.split())
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)


def detect_custom(pages: list[PageText], terms: list[str]) -> list[tuple]:
    out = []
    for page in pages:
        if not page.analyzed:
            continue
        for term in terms:
            for m in _pattern(term).finditer(page.text):
                out.append((page.page, "CUSTOM", m.start(), m.end(), 0.99, "Matches a term you entered"))
    return out


def propagate(pages: list[PageText], findings: list[Finding], level: str = "balanced") -> list[Finding]:
    """Flag every other occurrence of a value that was found once (same text, any case). Full person
    names also propagate their individual parts, which are often written alone later in a document."""
    part_min = profile(level)["name_parts"]
    by_page = {p.page: p for p in pages if p.analyzed}
    covered: dict[int, list] = {}
    for f in findings:
        covered.setdefault(f.page, []).append((f.start, f.end))
    seeds: dict[tuple, tuple] = {}
    for f in findings:
        if f.type == "CUSTOM":
            continue
        value = " ".join(f.text.split())
        if f.type == "PERSON_NAME":
            candidates = [value] + ([w.strip(".,;:") for w in value.split()
                                    if len(w.strip(".,;:")) >= part_min and w.strip(".,;:").isalpha()] if part_min else [])
        elif len(value) >= 4:
            candidates = [value]
        else:
            continue
        for candidate in candidates:
            seeds.setdefault((f.type, candidate.lower()), (candidate, f))
    added = []
    for (kind, _), (value, seed) in seeds.items():
        rx = _pattern(value)
        for number, page in by_page.items():
            for m in rx.finditer(page.text):
                if any(m.start() < e and m.end() > s for s, e in covered.get(number, [])):
                    continue
                covered.setdefault(number, []).append((m.start(), m.end()))
                added.append(Finding(
                    id=uuid.uuid4().hex[:12], page=number, type=kind, text=m.group(), start=m.start(), end=m.end(),
                    confidence=min(seed.confidence, 0.9) * 0.95, sources=["REPEAT"],
                    reason="Same value found elsewhere in the document",
                    rects=rects_for(page, m.start(), m.end())))
    return added
