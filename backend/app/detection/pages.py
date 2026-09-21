"""Build page text with word-offset mapping and classify pages."""
from .models import PageText

MIN_NATIVE_CHARS = 25
MIN_OCR_CONFIDENCE = 60.0


def build_pages(extracted: dict, ocr: dict | None = None) -> list[PageText]:
    """ocr: {page_number: {words, confidence}} replaces native words on scanned/mixed pages."""
    ocr = ocr or {}
    result = []
    for page in extracted["pages"]:
        ocr_page = ocr.get(page["page"])
        words = ocr_page["words"] if ocr_page else page["words"]
        parts, spans, cursor, previous = [], [], 0, None
        for x0, y0, x1, y1, word, block, line in words:
            key = (block, line)
            if parts:
                sep = "\n" if key != previous else " "
                parts.append(sep)
                cursor += 1
            parts.append(word)
            spans.append((cursor, cursor + len(word), x0, y0, x1, y1, key))
            cursor += len(word)
            previous = key
        text = "".join(parts)
        chars = sum(len(w[4]) for w in page["words"])  # classify by native text, not OCR output
        image = page["image_fraction"]
        if chars == 0 and image < 0.05:
            kind, analyzed = "EMPTY", True
        elif chars < MIN_NATIVE_CHARS and image >= 0.5:
            kind, analyzed = "SCANNED_IMAGE", False
        elif image >= 0.5:
            kind, analyzed = "MIXED", False  # large image may hold unread text; OCR not available yet
        else:
            kind, analyzed = "NATIVE_TEXT", True
        if ocr_page and kind in ("SCANNED_IMAGE", "MIXED"):
            # Low-confidence OCR is flagged for manual review rather than trusted as complete.
            analyzed = ocr_page["confidence"] >= MIN_OCR_CONFIDENCE
        result.append(PageText(page["page"], text, spans, kind, analyzed))
    return result


def needs_ocr(extracted: dict) -> list[int]:
    return [p.page for p in build_pages(extracted) if not p.analyzed]


def rects_for(page: PageText, start: int, end: int) -> list:
    """One merged rectangle per text line covered by [start, end)."""
    lines: dict = {}
    for s, e, x0, y0, x1, y1, key in page.spans:
        if e > start and s < end:
            r = lines.setdefault(key, [x0, y0, x1, y1])
            r[0], r[1], r[2], r[3] = min(r[0], x0), min(r[1], y0), max(r[2], x1), max(r[3], y1)
    return [[round(v, 2) for v in r] for r in lines.values()]
