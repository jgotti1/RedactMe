"""Generic form-label words ("Name", "Address", ...) are not sensitive values; never flag them."""
import re

LABEL_WORDS = {
    "name", "names", "first", "last", "middle", "full", "your", "spouse", "spouses", "spouse's", "taxpayer",
    "taxpayer's", "dependent", "dependents", "print", "printed", "type", "or", "and", "of", "the", "signature",
    "sign", "here", "date", "address", "home", "mailing", "street", "city", "state", "zip", "code", "apt", "no",
    "phone", "telephone", "email", "e-mail", "number", "social", "security", "ssn", "ein", "birth", "birthday",
    "dob", "occupation", "title", "employer", "employee", "filing", "status", "single", "married", "joint",
    "initial", "initials", "suffix", "county", "country", "foreign", "province", "postal", "account", "routing",
    "bank", "checking", "savings", "line", "form", "page", "total", "amount", "co", "inc", "llc", "ltd",
}


def is_label(text: str) -> bool:
    """True when every word of the text is a generic form-label word."""
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    return bool(words) and all(w.lower() in LABEL_WORDS for w in words)


def filter_raw(pages, raw):
    """Drop name/address candidates that are just label words; keep everything else unchanged."""
    by_page = {p.page: p for p in pages}
    kept = []
    for item in raw:
        page_no, kind, start, end = item[0], item[1], item[2], item[3]
        if kind in ("PERSON_NAME", "ADDRESS") and item[6] != "CUSTOM" and is_label(by_page[page_no].text[start:end]):
            continue
        kept.append(item)
    return kept
