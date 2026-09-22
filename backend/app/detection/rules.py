"""Deterministic, validated PII rules."""
import re

from .models import PageText
from .sensitivity import profile


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
    ("SSN", re.compile(r"(?<!\d)\d{3}[-\s]{1,2}\d{2}[-\s]{1,2}\d{4}(?!\d)"), _valid_ssn, 0.97, "Social Security Number format"),
    ("EIN", re.compile(r"(?<!\d)\d{2}-\d{7}(?!\d)"), None, 0.8, "Employer Identification Number format"),
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), None, 0.95, "Email address"),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"), None, 0.85, "Telephone number"),
    ("CREDIT_CARD", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
     lambda v: 13 <= len(re.sub(r"\D", "", v)) <= 19 and _luhn(re.sub(r"\D", "", v)), 0.95, "Payment card number (passes checksum)"),
    ("ADDRESS", re.compile(
        r"(?<!\d)\d{1,6}[ \t]+(?:[A-Za-z0-9.'-]+[ \t]+){1,4}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Terrace|Place|Pl|Parkway|Pkwy|Circle|Cir|Highway|Hwy)\b\.?"
        r"(?:,?[ \t]+(?:Apt|Apartment|Unit|Suite|Ste|#)\.?[ \t]*[A-Za-z0-9-]+)?"
        r"(?:,?[ \t]+[A-Za-z][A-Za-z .'-]{1,30},?[ \t]+[A-Z]{2}[ \t]+\d{5}(?:-\d{4})?)?"), None, 0.85, "Street address"),
]
NAME_STOP = {"the", "this", "that", "these", "those", "section", "article", "agreement", "party", "parties", "page",
             "form", "total", "line", "schedule", "exhibit", "united", "states", "state", "county", "department",
             "internal", "revenue", "service", "tax", "return", "income", "amount", "date", "number", "name",
             "address", "social", "security", "federal", "employer", "identification", "miscellaneous", "provisions"}
NAME_PAIR = re.compile(r"(?<![A-Za-z])[A-Z][a-z]{2,}(?:[ \t]+[A-Z]\.?)?[ \t]+[A-Z][a-z]{2,}(?![A-Za-z])")
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


LABEL_WINDOW = 120
SSN_LABEL = re.compile(r"social|\bssn\b|soc\.? ?sec", re.I)
ROUTING_LABEL = re.compile(r"routing|\baba\b|\brtn\b", re.I)
ACCOUNT_LABEL = re.compile(r"account|acct", re.I)


def _last(rx, text):
    found = [m.start() for m in rx.finditer(text)]
    return found[-1] if found else -1


def _digit_runs(page: PageText, prof: dict):
    """Numbers split across form cells (one line per cell, or one digit per cell) are rejoined into
    runs, then typed by the nearest preceding label. A line break only joins short digit-only lines,
    so two long adjacent fields (routing above account) are never merged."""
    text = page.text
    lines, offset = [], 0
    for raw in text.split("\n"):
        tokens = [(offset + m.start(), offset + m.end(), m.group()) for m in re.finditer(r"\S+", raw)]
        lines.append(tokens)
        offset += len(raw) + 1
    runs, chain = [], []          # each run: (tokens, cells) where cells means digits sit alone on their lines

    def flush():
        nonlocal chain
        if chain:
            runs.append((chain, True))
        chain = []
    for tokens in lines:
        digit_only = bool(tokens) and all(t[2].isdigit() for t in tokens)
        count = sum(len(t[2]) for t in tokens) if digit_only else 0
        if digit_only and count <= 4:
            chain.extend(tokens)            # short cell: may continue on the next short cell line
            continue
        flush()
        current = []
        for token in tokens:                 # ordinary line: consecutive digit tokens form a run
            if token[2].isdigit():
                current.append(token)
            else:
                if current:
                    runs.append((current, False))
                current = []
        if current:
            runs.append((current, digit_only))
    flush()
    out = []
    for run, cells in runs:
        digits = "".join(t[2] for t in run)
        start, end = run[0][0], run[-1][1]
        if cells:                             # form cells: the label sits above, within a few lines
            window = text[max(0, start - LABEL_WINDOW):start]
        else:                                 # inline number: only labels earlier on its own line count
            window = text[text.rfind("\n", 0, start) + 1:start]
        ssn, route, acct = _last(SSN_LABEL, window), _last(ROUTING_LABEL, window), _last(ACCOUNT_LABEL, window)
        n = len(digits)
        found = None
        if n == 9 and ssn >= 0 and ssn > route and ssn > acct and _valid_ssn(digits):
            found = ("SSN", 0.9, "Social Security number split across form cells")
        elif n == 9 and route >= 0 and _aba(digits):
            found = ("BANK_ROUTING", 0.9, "Routing number (passes checksum) in form cells")
        elif 4 <= n <= 17 and acct >= 0 and acct > route and acct > ssn:
            found = ("BANK_ACCOUNT", 0.85, "Number under an account label")
        elif prof["unlabeled"] and n == 9 and _valid_ssn(digits) and ssn < 0 and route < 0 and acct < 0:
            found = ("SSN", 0.5, "Nine-digit number that could be a Social Security number")
        elif prof["unlabeled"] and 8 <= n <= 17 and ssn < 0 and route < 0 and acct < 0:
            found = ("ID_NUMBER", 0.45, "Long number with no label")
        if found and (found[0] in prof["runs"] or found[2].startswith(("Nine", "Long"))):
            out.append((page.page, found[0], start, end, found[1], found[2]))
    return out


def detect(pages: list[PageText], level: str = "balanced") -> list[tuple]:
    """Return (page, type, start, end, confidence, reason) tuples."""
    prof = profile(level)
    out = []
    for page in pages:
        if not page.analyzed:
            continue
        text = page.text
        out.extend(_digit_runs(page, prof))
        for kind, rx, check, conf, reason in RULES:
            if (kind == "PHONE" and not prof["phone"]) or (kind == "EIN" and not prof["ein"]):
                continue
            for m in rx.finditer(text):
                if check is None or check(m.group()):
                    out.append((page.page, kind, m.start(), m.end(), conf, reason))
        for kind, rx, ctx, check, conf, reason in CONTEXTUAL:
            if kind not in prof["contextual"]:
                continue
            for m in rx.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                before = text[max(line_start, m.start() - CONTEXT):m.start()]
                # also accept a label on the previous line (form-style layouts)
                prev_start = text.rfind("\n", 0, max(line_start - 1, 0)) + 1
                above = text[prev_start:max(line_start - 1, 0)][-CONTEXT:]
                if ctx.search(before) or (line_start == m.start() and ctx.search(above)):
                    if check is None or check(m.group()):
                        out.append((page.page, kind, m.start(), m.end(), conf, reason))
        if prof["name_pairs"]:
            for m in NAME_PAIR.finditer(text):
                words = re.findall(r"[A-Za-z]{3,}", m.group())
                if not any(w.lower() in NAME_STOP for w in words):
                    out.append((page.page, "PERSON_NAME", m.start(), m.end(), 0.45, "Capitalized words that look like a name"))
    return out
