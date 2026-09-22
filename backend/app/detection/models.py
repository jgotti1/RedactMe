from dataclasses import dataclass, field


@dataclass
class PageText:
    page: int
    text: str
    # (start, end, x0, y0, x1, y1, line_key) per word, offsets into text
    spans: list
    classification: str  # NATIVE_TEXT | SCANNED_IMAGE | MIXED | EMPTY
    analyzed: bool


@dataclass
class Finding:
    id: str
    page: int
    type: str
    text: str  # raw value; kept server-side only
    start: int
    end: int
    confidence: float
    sources: list = field(default_factory=list)
    reason: str = ""
    recommend: bool = True
    rects: list = field(default_factory=list)
    levels: set = field(default_factory=set)  # sensitivity levels at which this finding is shown

    @staticmethod
    def mask(text: str) -> str:
        compact = text.strip()
        if len(compact) <= 4:
            return "•" * len(compact)
        return "•" * (len(compact) - 4) + compact[-4:]

    @property
    def level(self) -> str:
        return "HIGH" if self.confidence >= 0.85 else "MEDIUM" if self.confidence >= 0.6 else "LOW"

    def public(self):
        return {"id": self.id, "page": self.page, "type": self.type,
                "masked_text": self.mask(self.text), "level": self.level,
                "sources": sorted(self.sources), "reason": self.reason,
                "recommend_redaction": self.recommend, "rects": self.rects,
                "levels": sorted(self.levels)}
