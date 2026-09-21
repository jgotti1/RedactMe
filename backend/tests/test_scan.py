"""Scan pipeline tests: synthetic PDFs only; OpenAI is always mocked."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.detection import openai_service, pipeline
from app.documents.store import store
from app.main import app
from tests import make_sample_tax_return

FIX = Path(__file__).parent / "fixtures"
HEADERS = {"Authorization": "Bearer synthetic-token", "Content-Type": "application/pdf"}


@pytest.fixture(scope="module", autouse=True)
def fixtures():
    FIX.mkdir(exist_ok=True)
    make_sample_tax_return.build(FIX / "sample_tax_return.pdf")
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(FIX / "clean.pdf"))
    c.drawString(60, 740, "Quarterly newsletter: the library will be open extended hours this spring.")
    c.save()


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    store.clear()
    monkeypatch.setattr("app.auth.firebase.firebase_app", lambda: object())
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token",
                        lambda *a, **k: {"uid": "one", "email_verified": True})
    yield
    store.clear()


def fake_openai(monkeypatch, findings=None, fail=False):
    class Completions:
        async def create(self, **kwargs):
            if fail:
                raise RuntimeError("boom with 123-45-6789")
            body = json.dumps({"document_type": "1040", "findings": findings or []})
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=body))])

    class Client:
        def __init__(self, **k):
            self.chat = SimpleNamespace(completions=Completions())
        async def close(self):
            pass
    monkeypatch.setattr("openai.AsyncOpenAI", Client)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def scan(name):
    return asyncio.run(pipeline.scan((FIX / name).read_bytes()))


def test_tax_return_findings_with_ai(monkeypatch):
    fake_openai(monkeypatch, [
        {"page": 2, "type": "BANK_ACCOUNT", "text": "4931", "confidence": 0.9,
         "reason": "Partial account number", "recommend_redaction": True},
        {"page": 2, "type": "SSN", "text": "999-99-9999", "confidence": 0.9,  # hallucinated: absent
         "reason": "x", "recommend_redaction": True}])
    result = scan("sample_tax_return.pdf")
    assert result["complete"] and result["ai_status"] == "ok"
    found = {(f.page, f.type, f.text) for f in result["findings"]}
    assert (1, "SSN", "123-45-6789") in found
    assert (1, "SSN", "234-56-7891") in found
    assert (2, "BANK_ROUTING", "021000021") in found
    assert (2, "BANK_ACCOUNT", "4938291034") in found
    assert (2, "BANK_ACCOUNT", "4931") in found
    assert not any(f.text == "999-99-9999" for f in result["findings"])
    assert all(f.rects for f in result["findings"])
    assert all(len({f.id for f in result["findings"]}) == len(result["findings"]) for _ in [0])


def test_clean_pdf_is_complete_and_empty(monkeypatch):
    fake_openai(monkeypatch)
    result = scan("clean.pdf")
    assert result["complete"] and result["findings"] == []


def test_ai_failure_fails_closed(monkeypatch):
    fake_openai(monkeypatch, fail=True)
    result = scan("clean.pdf")
    assert result["ai_status"] == "failed" and not result["complete"]


def test_ai_disabled_is_incomplete(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(openai_service, "enabled", lambda: False)
    assert not scan("clean.pdf")["complete"]


def test_scanned_page_is_flagged_not_clean(monkeypatch):
    import pymupdf
    fake_openai(monkeypatch)
    with pymupdf.open() as src:
        page = src.new_page()
        page.insert_text((72, 72), "Synthetic image text", fontsize=30)
        pix = page.get_pixmap(dpi=100)
    with pymupdf.open() as doc:
        doc.new_page().insert_image(doc[0].rect, pixmap=pix)
        data = doc.tobytes()
    result = asyncio.run(pipeline.scan(data))
    assert result["unanalyzed_pages"] == [1] and not result["complete"]


def test_scan_endpoint_masks_values_and_requires_auth(monkeypatch):
    fake_openai(monkeypatch)
    with TestClient(app) as client:
        doc_id = str(uuid4())
        assert client.post(f"/api/documents/{doc_id}/scan").status_code == 401
        up = client.post(f"/api/documents/{doc_id}", headers=HEADERS,
                         content=(FIX / "sample_tax_return.pdf").read_bytes())
        assert up.status_code == 201
        res = client.post(f"/api/documents/{doc_id}/scan", headers={"Authorization": "Bearer x"})
        assert res.status_code == 200
        text = res.text
        for raw in ("123-45-6789", "4938291034", "021000021", "jordan.sample@example.com"):
            assert raw not in text
        assert res.json()["findings"]


def test_scan_unknown_or_other_users_document_is_404(monkeypatch):
    with TestClient(app) as client:
        assert client.post(f"/api/documents/{uuid4()}/scan", headers={"Authorization": "Bearer x"}).status_code == 404


def test_user_can_skip_ai_and_openai_is_not_called(monkeypatch):
    def boom(**k):
        raise AssertionError("OpenAI must not be constructed when skipped")
    monkeypatch.setattr("openai.AsyncOpenAI", boom)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    result = asyncio.run(pipeline.scan((FIX / "sample_tax_return.pdf").read_bytes(), use_ai=False))
    assert result["ai_status"] == "user_skipped" and result["complete"]
    assert any(f.type == "SSN" for f in result["findings"])
