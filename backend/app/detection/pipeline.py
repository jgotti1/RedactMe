"""Extract, classify, detect (rules + Presidio + OpenAI), merge."""
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

from . import openai_service, presidio_engine, rules
from .models import Finding
from .pages import build_pages, rects_for

SOURCE_PRIORITY = {"RULE": 3, "PRESIDIO": 2, "AI": 1}


async def _extract(data: bytes) -> dict:
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(Path(__file__).with_name("extractor.py")),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8", "PYTHONNOUSERSITE": "1"})
    try:
        output, _ = await asyncio.wait_for(process.communicate(data), timeout=30)
        result = json.loads(output)
        if process.returncode != 0 or "pages" not in result:
            raise ValueError
        return result
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.wait()


def merge(pages, raw):
    """raw: iterable of (page, type, start, end, confidence, reason, source)."""
    by_page = {p.page: p for p in pages}
    findings = []
    for page_no in sorted({r[0] for r in raw}):
        items = sorted((r for r in raw if r[0] == page_no), key=lambda r: (r[2], -r[3]))
        groups = []
        for item in items:
            if groups and item[2] < groups[-1]["end"]:
                groups[-1]["items"].append(item)
                groups[-1]["end"] = max(groups[-1]["end"], item[3])
            else:
                groups.append({"items": [item], "end": item[3]})
        for g in groups:
            best = max(g["items"], key=lambda r: (SOURCE_PRIORITY[r[6]] >= 2, r[4], r[3] - r[2]))
            page = by_page[page_no]
            text = page.text[best[2]:best[3]].strip()
            if not text:
                continue
            start = best[2] + (len(page.text[best[2]:best[3]]) - len(page.text[best[2]:best[3]].lstrip()))
            findings.append(Finding(
                id=uuid.uuid4().hex[:12], page=page_no, type=best[1], text=text, start=start,
                end=start + len(text), confidence=max(i[4] for i in g["items"]),
                sources=sorted({i[6] for i in g["items"]}), reason=best[5],
                rects=rects_for(page, start, start + len(text))))
    return findings


async def scan(data: bytes, use_ai: bool = True) -> dict:
    pages = build_pages(await _extract(data))
    raw = [(*t, "RULE") for t in rules.detect(pages)]
    raw += [(*t, "PRESIDIO") for t in await asyncio.to_thread(presidio_engine.detect, pages)]
    ai_raw, ai_status = await openai_service.analyze(pages) if use_ai else ([], "user_skipped")
    raw += [(*t, "AI") for t in ai_raw]
    findings = merge(pages, raw)
    unanalyzed = [p.page for p in pages if not p.analyzed]
    # A clean result may only be declared when every check ran on every page.
    complete = not unanalyzed and ai_status in ("ok", "user_skipped")  # skipping is the user's explicit choice
    return {"findings": findings, "ai_status": ai_status, "unanalyzed_pages": unanalyzed,
            "complete": complete,
            "pages": [{"page": p.page, "classification": p.classification, "analyzed": p.analyzed} for p in pages]}
