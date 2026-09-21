"""Microsoft Presidio (spaCy NER + built-in recognizers), loaded once lazily."""
from functools import lru_cache

from .models import PageText

ENTITIES = ["PERSON", "US_SSN", "US_ITIN", "US_BANK_NUMBER", "US_DRIVER_LICENSE", "US_PASSPORT",
            "CREDIT_CARD", "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE", "LOCATION"]
MAP = {"PERSON": "PERSON_NAME", "US_SSN": "SSN", "US_ITIN": "ID_NUMBER", "US_BANK_NUMBER": "BANK_ACCOUNT",
       "US_DRIVER_LICENSE": "ID_NUMBER", "US_PASSPORT": "ID_NUMBER", "CREDIT_CARD": "CREDIT_CARD",
       "EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE", "IBAN_CODE": "BANK_ACCOUNT", "LOCATION": "ADDRESS"}
MIN_SCORE = {"PERSON": 0.6, "LOCATION": 0.6}


@lru_cache(maxsize=1)
def _analyzer():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]})
    return AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])


def detect(pages: list[PageText]) -> list[tuple]:
    analyzer = _analyzer()
    out = []
    for page in pages:
        if not page.analyzed or not page.text.strip():
            continue
        for r in analyzer.analyze(text=page.text, language="en", entities=ENTITIES):
            if r.score < MIN_SCORE.get(r.entity_type, 0.4):
                continue
            end = r.end
            newline = page.text.find("\n", r.start, r.end)
            if newline != -1:  # NER can run across line breaks; a value never should
                end = newline
            if end <= r.start:
                continue
            out.append((page.page, MAP[r.entity_type], r.start, end, float(r.score),
                        f"Presidio: {r.entity_type.replace('_', ' ').title()}"))
    return out
