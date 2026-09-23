"""Bounded, single-worker, ephemeral document storage; no disk or database writes."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time

from fastapi import HTTPException

TTL_SECONDS = 15 * 60
MAX_DOCUMENTS = 10
MAX_ACTIVE_UPLOADS = 2


@dataclass
class Document:
    owner: str
    document_id: str
    deadline: float = field(default_factory=lambda: time.monotonic() + TTL_SECONDS)
    expires_at: str = field(default_factory=lambda: datetime.fromtimestamp(
        time.time() + TTL_SECONDS, timezone.utc).isoformat())
    data: bytearray = field(default_factory=bytearray)
    page_count: int = 0
    validated: bool = False
    scan: dict | None = None
    scanning: bool = False
    output: bytes | None = None
    redacting: bool = False
    verification_plan: str | None = None
    retained_warnings: dict = field(default_factory=dict)
    pending_warning: tuple | None = None

    def discard(self):
        # Release our buffer; Python/OS copies are not guaranteed secure erasure.
        self.data.clear()
        self.scan = None
        self.output = None
        self.verification_plan = None
        self.retained_warnings.clear()
        self.pending_warning = None

    def summary(self):
        return {"document_id": self.document_id, "status": "VALIDATED",
                "page_count": self.page_count, "size_bytes": len(self.data),
                "expires_at": self.expires_at}


class DocumentStore:
    def __init__(self):
        self.documents: dict[str, Document] = {}
        self.active: set[str] = set()
        self.cancelled: dict[tuple[str, str], float] = {}

    def expire(self):
        self.cancelled = {key: deadline for key, deadline in self.cancelled.items()
                          if deadline > time.monotonic()}
        for key, item in list(self.documents.items()):
            if item.deadline <= time.monotonic():
                self.remove(key, item.owner)

    def begin(self, document_id, owner):
        self.expire()
        if (owner, document_id) in self.cancelled:
            raise HTTPException(409, "The upload was cancelled. Choose the file again.")
        if len(self.cancelled) >= 1000:
            raise HTTPException(503, "The workspace is busy. Please try again shortly.")
        if owner in self.active or len(self.active) >= MAX_ACTIVE_UPLOADS:
            raise HTTPException(429, "An upload is already in progress. Please try again shortly.")
        if document_id in self.documents:
            raise HTTPException(409, "Please choose the file again to begin a new upload.")
        # A new upload replaces this user's old temporary document.
        for key, item in list(self.documents.items()):
            if item.owner == owner:
                self.remove(key, owner)
        if len(self.documents) >= MAX_DOCUMENTS:
            raise HTTPException(503, "The workspace is busy. Please try again shortly.")
        item = Document(owner, document_id)
        self.documents[document_id] = item
        self.active.add(owner)
        return item

    def remove(self, document_id, owner):
        item = self.documents.get(document_id)
        if item and item.owner == owner:
            self.documents.pop(document_id)
            # In-flight data is owned by its request until validation exits.
            if item.validated:
                item.discard()

    def cancel(self, document_id, owner):
        self.expire()
        self.remove(document_id, owner)
        # A DELETE can arrive before a cancelled POST has finished authenticating.
        if len(self.cancelled) < 1000:
            self.cancelled[(owner, document_id)] = time.monotonic() + TTL_SECONDS

    def clear(self):
        for item in self.documents.values():
            item.discard()
        self.documents.clear()
        self.active.clear()
        self.cancelled.clear()


store = DocumentStore()
