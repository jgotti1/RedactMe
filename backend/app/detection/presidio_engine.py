"""Microsoft Presidio (spaCy NER + built-in recognizers), loaded once lazily."""
from functools import lru_cache

from .models import PageText
from .sensitivity import profile

ENTITIES = ["PERSON", "US_SSN", "US_ITIN", "US_BANK_NUMBER", "US_DRIVER_LICENSE", "US_PASSPORT",
            "CREDIT_CARD", "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE", "LOCATION"]
MAP = {"PERSON": "PERSON_NAME", "US_SSN": "SSN", "US_ITIN": "ID_NUMBER", "US_BANK_NUMBER": "BANK_ACCOUNT",
       "US_DRIVER_LICENSE": "ID_NUMBER", "US_PASSPORT": "ID_NUMBER", "CREDIT_CARD": "CREDIT_CARD",
       "EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE", "IBAN_CODE": "BANK_ACCOUNT", "LOCATION": "ADDRESS"}


def _model_name() -> str:
    import spacy.util

    # Prefer the more accurate medium model; fall back to the small one if it is not installed.
    for name in ("en_core_web_md", "en_core_web_sm"):
        if spacy.util.is_package(name):
            return name
    raise RuntimeError("No spaCy English model installed")


@lru_cache(maxsize=1)
def _analyzer():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": _model_name()}]})
    return AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])


def analyze(pages: list[PageText]) -> list[tuple]:
    """Run the model once at the loosest thresholds; select() applies each sensitivity level."""
    analyzer = _analyzer()
    out = []
    for page in pages:
        if not page.analyzed or not page.text.strip():
            continue
        for r in analyzer.analyze(text=page.text, language="en", entities=ENTITIES):
            out.append((page.page, r.entity_type, r.start, r.end, float(r.score)))
    return out


def select(results: list[tuple], pages: list[PageText], level: str = "balanced") -> list[tuple]:
    prof = profile(level)
    by_page = {p.page: p for p in pages}
    out = []
    for page_no, entity, start, end, score in results:
        if entity == "LOCATION" and prof["location"] is None:
            continue  # Low sensitivity: street addresses come from the address rule only
        minimum = prof["person"] if entity == "PERSON" else prof["location"] if entity == "LOCATION" else prof["other"]
        if score < minimum:
            continue
        newline = by_page[page_no].text.find("\n", start, end)
        if newline != -1:  # NER can run across line breaks; a value never should
            end = newline
        if end <= start:
            continue
        out.append((page_no, MAP[entity], start, end, score, f"Presidio: {entity.replace('_', ' ').title()}"))
    return out


def detect(pages: list[PageText], level: str = "balanced") -> list[tuple]:
    return select(analyze(pages), pages, level)
