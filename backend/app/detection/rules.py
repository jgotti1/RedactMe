"""Deterministic, validated PII rules."""
import re

from .models import PageText


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def _aba(digits: str) -> bool:
    w = (3, 7, 1) * 3
    return len(digits) == 9 and sum(int(d) * k for d, k in zip(digits, w)) % 10 == 0


def _valid_ssn(v: str) -> bool:
    a, g, s = re.sub(r"\D", "", v)[:3], re.sub(r"\D", "", v)[3:5], re.sub(r"\D", "", v)[5:]
    return a not in ("000", "666") and not a.startswith("9") and g != "00" and s != "0000"


CONTEXT = 60
RULES = [
    ("SSN", re.compile(r"(?<!\d)\d{3}[- ]\d{2}[- ]\d{4}(?!\d)"), _valid_ssn, 0.97, "Social Security Number format"),
    ("EIN", re.compile(r"(?<!\d)\d{2}-\d{7}(?!\d)"), None, 0.8, "Employer Identification Number format"),
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), None, 0.95, "Email address"),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"), None, 0.85, "Telephone number"),
    ("CREDIT_CARD", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
     lambda v: 13 <= len(re.sub(r"\D", "", v)) <= 19 and _luhn(re.sub(r"\D", "", v)), 0.95, "Payment card number (passes checksum)"),
]
CONTEXTUAL = [
    ("BANK_ROUTING", re.compile(r"(?<!\d)\d{9}(?!\d)"), re.compile(r"routing|\baba\b|\brtn\b", re.I),
     lambda v: _aba(v), 0.95, "Bank routing number (passes checksum) near routing label"),
    ("BANK_ACCOUNT", re.compile(r"(?<![\d-])\d{4,17}(?![\d-])"), re.compile(r"account|acct", re.I),
     None, 0.85, "Number near a bank account label"),
    ("DATE_OF_BIRTH", re.compile(r"(?<!\d)(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})(?!\d)"),
     re.compile(r"birth|\bdob\b|born", re.I), None, 0.9, "Date near a birth label"),
    ("ID_NUMBER", re.compile(r"(?<![A-Za-z0-9])[A-Z0-9]{6,12}(?![A-Za-z0-9])"),
     re.compile(r"driver'?s? licen[sc]e|passport|\bdl\b|id number|itin|pin\b", re.I),
     lambda v: any(c.isdigit() for c in v), 0.8, "Identification number near an ID label"),
]


def detect(pages: list[PageText]) -> list[tuple]:
    """Return (page, type, start, end, confidence, reason) tuples."""
    out = []
    for page in pages:
        if not page.analyzed:
            continue
        text = page.text
        for kind, rx, check, conf, reason in RULES:
            for m in rx.finditer(text):
                if check is None or check(m.group()):
                    out.append((page.page, kind, m.start(), m.end(), conf, reason))
        for kind, rx, ctx, check, conf, reason in CONTEXTUAL:
            for m in rx.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                before = text[max(line_start, m.start() - CONTEXT):m.start()]
                # also accept a label on the previous line (form-style layouts)
                prev_start = text.rfind("\n", 0, max(line_start - 1, 0)) + 1
                above = text[prev_start:max(line_start - 1, 0)][-CONTEXT:]
                if ctx.search(before) or (line_start == m.start() and ctx.search(above)):
                    if check is None or check(m.group()):
                        out.append((page.page, kind, m.start(), m.end(), conf, reason))
    return out
