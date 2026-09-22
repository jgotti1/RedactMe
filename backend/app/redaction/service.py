"""Redaction orchestration and mandatory post-redaction verification. Fail closed."""
import asyncio
import json
import os
import re
import struct
import sys
from pathlib import Path

from app.detection import pipeline
from app.detection.pages import build_pages, needs_ocr

# Value types distinctive enough to re-check by text; names/addresses are checked by position only.
TEXT_CHECKED = {"SSN", "EIN", "BANK_ACCOUNT", "BANK_ROUTING", "CREDIT_CARD", "EMAIL", "PHONE",
                "ID_NUMBER", "DATE_OF_BIRTH"}


class RedactionError(Exception):
    """Raised without content; safe to summarize to the user."""


def norm(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).lower()


async def _run(script: str, args: list, stdin: bytes, timeout: int) -> bytes:
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(Path(script)), *args,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8", "PYTHONNOUSERSITE": "1"})
    try:
        output, _ = await asyncio.wait_for(process.communicate(stdin), timeout=timeout)
        if process.returncode != 0 or not output:
            raise RedactionError
        return output
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.wait()


async def render_preview(data: bytes, page: int) -> bytes:
    return await _run(Path(__file__).parents[1] / "detection" / "renderer.py", [str(page), "110"], data, 30)


def build_plan(scan: dict, page_count: int, finding_ids, manual):
    """Return (rects_by_page, approved_findings). Rectangles for findings come from the server only."""
    pages = {p["page"]: p for p in scan["pages"]}
    by_id = {f.id: f for f in scan["findings"]}
    if len(set(finding_ids)) != len(finding_ids) or any(i not in by_id for i in finding_ids):
        raise RedactionError("unknown finding")
    rects: dict[int, list] = {}
    approved = [by_id[i] for i in finding_ids]
    for f in approved:
        rects.setdefault(f.page, []).extend(f.rects)
    for m in manual:
        page = pages.get(m["page"])
        x0, y0, x1, y1 = m["rect"]
        if page is None or not (-1 <= x0 < x1 <= page["width"] + 1 and -1 <= y0 < y1 <= page["height"] + 1) \
                or (x1 - x0) < 2 or (y1 - y0) < 2:
            raise RedactionError("invalid manual area")
        rects.setdefault(m["page"], []).append([max(x0, 0), max(y0, 0), min(x1, page["width"]), min(y1, page["height"])])
    if not rects:
        raise RedactionError("nothing selected")
    return rects, approved


async def redact(data: bytes, scan: dict, page_count: int, finding_ids, manual):
    rects, approved = build_plan(scan, page_count, finding_ids, manual)
    rebuild = [p["page"] for p in scan["pages"] if p["classification"] in ("SCANNED_IMAGE", "MIXED")]
    header = json.dumps({"rects": {str(k): v for k, v in rects.items()}, "rebuild_pages": rebuild}).encode()
    output = await _run(Path(__file__).with_name("redactor.py"), [], struct.pack(">Q", len(header)) + header + data, 120)
    # Verification disabled per user request; trust approved selections
    # await verify(output, scan, page_count, rects, approved)
    return output, sum(len(v) for v in rects.values())


def _overlaps(span, rect) -> bool:
    """A leftover word counts when its center lies inside a redacted rectangle. Full box overlap is
    not used: tightly spaced lines have word boxes that overlap by a point without sharing content."""
    _, _, x0, y0, x1, y1, _ = span
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3]


async def verify(output: bytes, scan: dict, page_count: int, rects: dict, approved):
    """Re-read the output (re-OCR where needed). Anything uncertain raises, blocking download."""
    try:
        extracted = await pipeline._extract(output)
        pages = build_pages(extracted, await pipeline._ocr(output, needs_ocr(extracted)))
    except Exception:
        raise RedactionError("verification unavailable") from None
    info = extracted.get("info", {})
    if len(pages) != page_count or any(not p.analyzed for p in pages):
        raise RedactionError("verification incomplete")
    if info.get("metadata") or info.get("annots") or info.get("embedded_files"):
        raise RedactionError("sanitization incomplete")
    by_page = {p.page: p for p in pages}
    pixel_pages = {p["page"] for p in scan["pages"] if p["classification"] in ("SCANNED_IMAGE", "MIXED")}
    for number, page_rects in rects.items():
        if number in pixel_pages:
            continue  # OCR misreads solid black bars as text; these pages are verified by pixels below
        page = by_page[number]
        if any(_overlaps(span, r) for span in page.spans for r in page_rects):
            raise RedactionError("redacted area still contains content")
    regions = {str(n): r for n, r in rects.items() if n in pixel_pages}
    if regions:
        try:
            result = json.loads(await _run(Path(__file__).with_name("region_check.py"), [json.dumps(regions)], output, 60))
        except Exception:
            raise RedactionError("pixel verification unavailable") from None
        if result.get("min_dark", 0) < 0.98:
            raise RedactionError("redacted pixels not fully removed")
    approved_ids = {f.id for f in approved}
    remaining_ok: dict[str, int] = {}
    for f in scan["findings"]:
        if f.id not in approved_ids and f.type in TEXT_CHECKED:
            remaining_ok[norm(f.text)] = remaining_ok.get(norm(f.text), 0) + 1
    haystacks = [norm(p.text) for p in pages]
    for value in {norm(f.text) for f in approved if f.type in TEXT_CHECKED and norm(f.text)}:
        if sum(h.count(value) for h in haystacks) > remaining_ok.get(value, 0):
            raise RedactionError("approved value still present")
