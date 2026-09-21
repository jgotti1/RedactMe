"""Authenticated temporary PDF upload, scan, review, redaction and download."""
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field
from app.redaction import service as redaction
from starlette.requests import ClientDisconnect

from app.auth.firebase import require_user
from app.detection import pipeline
from .store import store
from .validator import MAX_BYTES, MAX_PAGES

router = APIRouter(prefix="/api/documents", tags=["Documents"])


def document_user(user: Annotated[dict, Depends(require_user)]):
    if user.get("email_verified") is not True:
        raise HTTPException(403, "Verify your email address before uploading a PDF.")
    return user


async def validate_pdf(data):
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(Path(__file__).with_name("validator.py")),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8", "PYTHONNOUSERSITE": "1"},
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(data), timeout=15)
        if process.returncode != 0:
            raise HTTPException(422, "This PDF could not be validated within safe limits. The upload was discarded.")
        try:
            result = json.loads(output)
        except (ValueError, TypeError):
            raise HTTPException(422, "This PDF could not be validated. The upload was discarded.") from None
        messages = {
            "size": "This PDF exceeds the 20 MB limit. Upload a smaller PDF.",
            "empty_file": "This file is empty (0 bytes) and contains no PDF data. Export or download it again.",
            "image_file": "This file appears to be an image, not a PDF, even if its filename ends in .pdf. Export the image as a PDF and try again.",
            "not_pdf": "This file does not contain a PDF header. It may be a different file type renamed to .pdf. Export or download a real PDF.",
            "corrupt": "This PDF appears corrupted or incomplete: its structure or page data could not be read reliably. Export or download a fresh copy.",
            "no_pages": "This PDF has no pages. Upload a PDF containing document pages.",
            "no_content": "This PDF has no content: all pages appear empty, with no text, images, drawings or annotations to review.",
            "encrypted": "Password-protected PDFs are not supported. Upload an unlocked copy.",
            "pages": f"Choose a PDF containing 1 to {MAX_PAGES} pages.",
            "invalid": "This file is not a valid, readable PDF. Export a new PDF and try again.",
        }
        if result.get("error") or not isinstance(result.get("page_count"), int):
            raise HTTPException(422, messages.get(result.get("error"), messages["invalid"]) + " The upload was discarded.")
        return result["page_count"]
    except asyncio.TimeoutError:
        raise HTTPException(422, "PDF validation timed out. The upload was discarded.") from None
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.wait()


@router.post("/{document_id}", status_code=201, summary="Upload and validate a PDF")
async def upload_pdf(document_id: UUID, request: Request,
                     user: Annotated[dict, Depends(document_user)]):
    key = str(document_id)
    item = store.begin(key, user["uid"])
    succeeded = False
    try:
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/pdf":
            raise HTTPException(415, "Only PDF uploads are accepted. The upload was discarded.")
        # The counted stream is authoritative, even with a missing/false Content-Length.
        length = request.headers.get("content-length")
        if length is not None:
            try:
                size = int(length)
            except ValueError:
                raise HTTPException(400, "Invalid upload size. The upload was discarded.") from None
            if size == 0:
                raise HTTPException(422, "This file is empty (0 bytes) and contains no PDF data. The upload was discarded.")
            if size < 0 or size > MAX_BYTES:
                raise HTTPException(413, "Choose a nonempty PDF no larger than 20 MB. The upload was discarded.")
        async def receive():
            async for chunk in request.stream():
                if store.documents.get(key) is not item:
                    raise HTTPException(409, "The upload was cancelled or expired.")
                if len(item.data) + len(chunk) > MAX_BYTES:
                    raise HTTPException(413, "The PDF exceeds 20 MB. The upload was discarded.")
                item.data.extend(chunk)
        await asyncio.wait_for(receive(), timeout=45)
        item.page_count = await validate_pdf(item.data)
        if await request.is_disconnected() or store.documents.get(key) is not item:
            raise HTTPException(409, "The upload was cancelled or expired.")
        item.validated = True
        succeeded = True
        return item.summary()
    except OSError:
        raise HTTPException(503, "PDF validation is unavailable. The upload was discarded.") from None
    except (asyncio.TimeoutError, ClientDisconnect):
        raise HTTPException(408, "Upload interrupted or timed out. The upload was discarded.") from None
    finally:
        store.active.discard(user["uid"])
        if not succeeded:
            store.remove(key, user["uid"])
            item.discard()


@router.get("/{document_id}", summary="Check temporary PDF status")
async def document_status(document_id: UUID, user: Annotated[dict, Depends(document_user)]):
    store.expire()
    item = store.documents.get(str(document_id))
    if not item or item.owner != user["uid"] or not item.validated:
        raise HTTPException(404, "This upload is unavailable or expired. Please upload the PDF again.")
    return item.summary()


@router.post("/{document_id}/scan", summary="Scan a temporary PDF for sensitive information")
async def scan_pdf(document_id: UUID, user: Annotated[dict, Depends(document_user)],
                   use_ai: bool = True):
    store.expire()
    item = store.documents.get(str(document_id))
    if not item or item.owner != user["uid"] or not item.validated:
        raise HTTPException(404, "This upload is unavailable or expired. Please upload the PDF again.")
    if item.scanning:
        raise HTTPException(409, "A scan is already running for this document.")
    item.scanning = True
    try:
        result = await asyncio.wait_for(pipeline.scan(bytes(item.data), use_ai), timeout=240)
    except Exception:
        # Fail closed and never echo parser/model errors, which may contain document content.
        raise HTTPException(502, "The scan could not be completed, so no review is available. Please try again.") from None
    finally:
        item.scanning = False
    if store.documents.get(str(document_id)) is not item:
        raise HTTPException(409, "The upload was cancelled or expired.")
    item.scan = result
    return {"document_id": item.document_id, "status": "SCANNED", "complete": result["complete"],
            "ai_status": result["ai_status"], "unanalyzed_pages": result["unanalyzed_pages"],
            "pages": [{k: p[k] for k in ("page", "classification", "analyzed", "width", "height")}
                      for p in result["pages"]], "page_count": item.page_count, "expires_at": item.expires_at,
            "findings": [f.public() for f in result["findings"]]}


class ManualArea(BaseModel):
    page: int = Field(ge=1, le=200)
    rect: list[float] = Field(min_length=4, max_length=4)


class RedactRequest(BaseModel):
    finding_ids: list[str] = Field(default_factory=list, max_length=2000)
    manual: list[ManualArea] = Field(default_factory=list, max_length=200)


def _owned(document_id: UUID, user: dict):
    store.expire()
    item = store.documents.get(str(document_id))
    if not item or item.owner != user["uid"] or not item.validated:
        raise HTTPException(404, "This upload is unavailable or expired. Please upload the PDF again.")
    return item


@router.get("/{document_id}/pages/{page}/preview", summary="Render a page preview")
async def page_preview(document_id: UUID, page: int, user: Annotated[dict, Depends(document_user)]):
    item = _owned(document_id, user)
    if not 1 <= page <= item.page_count:
        raise HTTPException(404, "Page not found.")
    try:
        png = await redaction.render_preview(bytes(item.data), page)
    except Exception:
        raise HTTPException(502, "The page preview could not be created.") from None
    return Response(png, media_type="image/png")


@router.post("/{document_id}/redact", summary="Apply approved redactions and verify the result")
async def redact_pdf(document_id: UUID, body: RedactRequest, user: Annotated[dict, Depends(document_user)]):
    item = _owned(document_id, user)
    if item.scan is None:
        raise HTTPException(409, "Scan the document before redacting.")
    if item.redacting:
        raise HTTPException(409, "Redaction is already running for this document.")
    item.redacting = True
    item.output = None
    try:
        output, count = await asyncio.wait_for(redaction.redact(
            bytes(item.data), item.scan, item.page_count, body.finding_ids,
            [m.model_dump() for m in body.manual]), timeout=300)
    except redaction.RedactionError as error:
        message = str(error)
        if message in ("unknown finding", "invalid manual area", "nothing selected"):
            raise HTTPException(422, "Choose at least one valid redaction before continuing.") from None
        safe_reasons = {
            "verification unavailable": "Verification could not read the output PDF.",
            "verification incomplete": "One or more output pages could not be fully verified, including OCR where required.",
            "sanitization incomplete": "The output still contains metadata or attachments that must be removed.",
            "redacted area still contains content": "Content remains inside a selected redaction area.",
            "pixel verification unavailable": "The redacted image regions could not be verified.",
            "redacted pixels not fully removed": "A selected image region was not fully redacted.",
            "approved value still present": "An approved sensitive value still appears in the output.",
        }
        reason = safe_reasons.get(message, "The output PDF could not be verified.")
        raise HTTPException(422, reason + " Download is blocked; nothing was released.") from None
    except Exception:
        raise HTTPException(502, "Redaction could not be completed and nothing was released. Please try again.") from None
    finally:
        item.redacting = False
    if store.documents.get(str(document_id)) is not item:
        raise HTTPException(409, "The upload was cancelled or expired.")
    item.output = output
    return {"document_id": item.document_id, "status": "VERIFIED", "redaction_count": count,
            "size_bytes": len(output), "expires_at": item.expires_at}


@router.get("/{document_id}/download", summary="Download the verified redacted PDF (single use)")
async def download_pdf(document_id: UUID, user: Annotated[dict, Depends(document_user)]):
    item = _owned(document_id, user)
    if not item.output:
        raise HTTPException(409, "No verified redacted file is available.")
    content = bytes(item.output)
    key, owner = str(document_id), user["uid"]

    def purge():  # single use: original, output and findings are discarded after sending
        current = store.documents.get(key)
        if current is item:
            store.remove(key, owner)
            item.discard()
    return Response(content, media_type="application/pdf", background=BackgroundTask(purge),
                    headers={"Content-Disposition": 'attachment; filename="redacted.pdf"'})


@router.delete("/{document_id}", status_code=204, summary="Discard a temporary PDF")
async def delete_pdf(document_id: UUID, user: Annotated[dict, Depends(require_user)]):
    # Idempotent; never reveal whether another user's document exists.
    store.cancel(str(document_id), user["uid"])
    return Response(status_code=204)
