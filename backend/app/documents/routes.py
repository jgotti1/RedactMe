"""Authenticated upload validation; deliberately no scan or download endpoints."""
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
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
            "size": "Choose a nonempty PDF no larger than 20 MB.",
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
            if size <= 0 or size > MAX_BYTES:
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
            "pages": result["pages"], "page_count": item.page_count, "expires_at": item.expires_at,
            "findings": [f.public() for f in result["findings"]]}


@router.delete("/{document_id}", status_code=204, summary="Discard a temporary PDF")
async def delete_pdf(document_id: UUID, user: Annotated[dict, Depends(require_user)]):
    # Idempotent; never reveal whether another user's document exists.
    store.cancel(str(document_id), user["uid"])
    return Response(status_code=204)
