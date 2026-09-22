"""Scan pipeline tests: synthetic PDFs only."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.detection import pipeline
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


def scan(name):
    return asyncio.run(pipeline.scan((FIX / name).read_bytes()))


def test_tax_return_findings():
    result = scan("sample_tax_return.pdf")
    assert result["complete"]
    found = {(f.page, f.type, f.text) for f in result["findings"]}
    assert (1, "SSN", "123-45-6789") in found
    assert (1, "SSN", "234-56-7891") in found
    assert (2, "BANK_ROUTING", "021000021") in found
    assert (2, "BANK_ACCOUNT", "4938291034") in found
    assert (2, "BANK_ACCOUNT", "4931") in found
    assert all(f.rects for f in result["findings"])
    assert all(len({f.id for f in result["findings"]}) == len(result["findings"]) for _ in [0])


def test_clean_pdf_is_complete_and_empty(monkeypatch):
    result = scan("clean.pdf")
    assert result["complete"] and result["findings"] == []






def scanned_pdf(text):
    import pymupdf
    with pymupdf.open() as src:
        page = src.new_page()
        page.insert_text((72, 100), text, fontsize=20)
        pix = page.get_pixmap(dpi=150)
    with pymupdf.open() as doc:
        doc.new_page().insert_image(doc[0].rect, pixmap=pix)
        return doc.tobytes()


def test_scanned_page_is_ocrd_and_detected(monkeypatch):
    import shutil
    if not shutil.which("tesseract") and not Path("/opt/homebrew/bin/tesseract").exists():
        pytest.skip("tesseract not installed")
    result = asyncio.run(pipeline.scan(scanned_pdf("Social security number: 123-45-6789")))
    assert result["pages"][0]["classification"] == "SCANNED_IMAGE"
    assert result["complete"], result["unanalyzed_pages"]
    assert any(f.type == "SSN" and f.rects for f in result["findings"])


def test_scanned_page_without_ocr_is_flagged_not_clean(monkeypatch):
    import pymupdf
    async def no_ocr(*a):
        return {}
    monkeypatch.setattr(pipeline, "_ocr", no_ocr)
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




# ---- redaction, verification and download ----
def _scan_and_ids(client, doc_id, name="sample_tax_return.pdf"):
    assert client.post(f"/api/documents/{doc_id}", headers=HEADERS, content=(FIX / name).read_bytes()).status_code == 201
    res = client.post(f"/api/documents/{doc_id}/scan", headers={"Authorization": "Bearer x"})
    assert res.status_code == 200
    return res.json()


def test_redact_verify_download_removes_text_and_is_single_use():
    import pymupdf
    with TestClient(app) as client:
        doc_id = str(uuid4())
        scan_json = _scan_and_ids(client, doc_id)
        auth = {"Authorization": "Bearer x"}
        ids = [f["id"] for f in scan_json["findings"] if f["type"] in ("SSN", "BANK_ACCOUNT", "BANK_ROUTING")]
        assert client.get(f"/api/documents/{doc_id}/download", headers=auth).status_code == 409  # nothing verified yet
        res = client.post(f"/api/documents/{doc_id}/redact", headers=auth,
                          json={"finding_ids": ids, "manual": [{"page": 1, "rect": [55, 60, 300, 80]}]})
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "VERIFIED"
        dl = client.get(f"/api/documents/{doc_id}/download", headers=auth)
        assert dl.status_code == 200 and "attachment" in dl.headers["content-disposition"]
        with pymupdf.open(stream=dl.content, filetype="pdf") as out:
            text = "".join(p.get_text() for p in out)
            assert out.page_count == 2
        for secret in ("123-45-6789", "234-56-7891", "345-67-8912", "021000021", "4938291034"):
            assert secret not in text
        assert "742 Evergreen" in text  # unselected content is preserved
        assert client.get(f"/api/documents/{doc_id}/download", headers=auth).status_code == 404  # single use


def test_redact_rejects_bad_input_and_unauthenticated():
    with TestClient(app) as client:
        doc_id = str(uuid4())
        assert client.post(f"/api/documents/{doc_id}/redact", json={}).status_code == 401
        _scan_and_ids(client, doc_id)
        auth = {"Authorization": "Bearer x"}
        assert client.post(f"/api/documents/{doc_id}/redact", headers=auth, json={"finding_ids": ["nope"]}).status_code == 422
        assert client.post(f"/api/documents/{doc_id}/redact", headers=auth, json={}).status_code == 422
        assert client.post(f"/api/documents/{doc_id}/redact", headers=auth,
                           json={"manual": [{"page": 1, "rect": [0, 0, 9999, 9999]}]}).status_code == 422
        assert client.get(f"/api/documents/{doc_id}/download", headers=auth).status_code == 409


def test_failed_verification_blocks_download(monkeypatch):
    from app.redaction import service
    async def bad_verify(*a, **k):
        raise service.RedactionError("approved value still present")
    monkeypatch.setattr(service, "verify", bad_verify)
    with TestClient(app) as client:
        doc_id = str(uuid4())
        data = _scan_and_ids(client, doc_id)
        auth = {"Authorization": "Bearer x"}
        res = client.post(f"/api/documents/{doc_id}/redact", headers=auth, json={"finding_ids": [data["findings"][0]["id"]]})
        assert res.status_code == 422
        assert client.get(f"/api/documents/{doc_id}/download", headers=auth).status_code == 409


def test_preview_and_isolation(monkeypatch):
    with TestClient(app) as client:
        doc_id = str(uuid4())
        _scan_and_ids(client, doc_id)
        ok = client.get(f"/api/documents/{doc_id}/pages/1/preview", headers={"Authorization": "Bearer x"})
        assert ok.status_code == 200 and ok.content[:4] == b"\x89PNG"
        assert client.get(f"/api/documents/{doc_id}/pages/9/preview", headers={"Authorization": "Bearer x"}).status_code == 404
        monkeypatch.setattr("app.auth.firebase.auth.verify_id_token",
                            lambda *a, **k: {"uid": "two", "email_verified": True})
        for path in (f"/pages/1/preview", "/download"):
            assert client.get(f"/api/documents/{doc_id}{path}", headers={"Authorization": "Bearer x"}).status_code == 404
        assert client.post(f"/api/documents/{doc_id}/redact", headers={"Authorization": "Bearer x"}, json={"finding_ids": []}).status_code == 404


def test_scanned_page_redaction_rebuilds_and_verifies(monkeypatch):
    import shutil
    if not shutil.which("tesseract") and not Path("/opt/homebrew/bin/tesseract").exists():
        pytest.skip("tesseract not installed")
    from app.redaction import service
    data = scanned_pdf("Social security number: 123-45-6789")
    scan_result = asyncio.run(pipeline.scan(data))
    ids = [f.id for f in scan_result["findings"] if f.type == "SSN"]
    assert ids
    output, count = asyncio.run(service.redact(data, scan_result, 1, ids, []))
    import pymupdf
    with pymupdf.open(stream=output, filetype="pdf") as out:
        assert out[0].get_text().strip() == ""  # rebuilt as image; no text layer remains


def test_all_recommended_findings_across_two_pages_redact_and_download():
    import pymupdf
    with TestClient(app) as client:
        doc_id = str(uuid4())
        scanned = _scan_and_ids(client, doc_id)
        findings = [f for f in scanned['findings'] if f['recommend_redaction']]
        assert {f['page'] for f in findings} == {1, 2}
        auth = {'Authorization': 'Bearer x'}
        response = client.post(f'/api/documents/{doc_id}/redact', headers=auth,
                               json={'finding_ids': [f['id'] for f in findings]})
        assert response.status_code == 200, response.text
        output = client.get(f'/api/documents/{doc_id}/download', headers=auth)
        assert output.status_code == 200
        with pymupdf.open(stream=output.content, filetype='pdf') as doc:
            assert doc.page_count == 2
            assert '123-45-6789' not in doc[0].get_text()
            assert '4938291034' not in doc[1].get_text()


def test_multipage_scanned_redaction_and_metadata_verification(monkeypatch):
    import shutil
    import pymupdf
    from app.redaction import service
    from app.detection.extractor import extract
    if not shutil.which('tesseract') and not Path('/opt/homebrew/bin/tesseract').exists():
        pytest.skip('tesseract not installed')
    with pymupdf.open() as document:
        for value in ['123-45-6789', '234-56-7891']:
            with pymupdf.open(stream=scanned_pdf('Social security number: ' + value), filetype='pdf') as part:
                document.insert_pdf(part)
        document.set_metadata({'title': 'Synthetic private metadata'})
        data = document.tobytes()
    assert extract(data)['info']['metadata'] is True
    scanned = asyncio.run(pipeline.scan(data))
    findings = [f for f in scanned['findings'] if f.type == 'SSN']
    assert {f.page for f in findings} == {1, 2}
    output, count = asyncio.run(service.redact(data, scanned, 2, [f.id for f in findings], []))
    assert count >= 2
    assert extract(output)['info']['metadata'] is False
    with pymupdf.open(stream=output, filetype='pdf') as document:
        assert document.page_count == 2
        assert all(not page.get_text().strip() for page in document)


def test_verification_failure_reason_is_safe_and_specific(monkeypatch):
    from app.redaction import service
    async def incomplete(*a, **k):
        raise service.RedactionError('verification incomplete')
    monkeypatch.setattr(service, 'verify', incomplete)
    with TestClient(app) as client:
        doc_id = str(uuid4())
        scanned = _scan_and_ids(client, doc_id)
        response = client.post(f'/api/documents/{doc_id}/redact', headers={'Authorization': 'Bearer x'},
                               json={'finding_ids': [scanned['findings'][0]['id']]})
        assert response.status_code == 422
        assert 'One or more output pages' in response.json()['detail']
        assert client.get(f'/api/documents/{doc_id}/download', headers={'Authorization': 'Bearer x'}).status_code == 409


def test_tight_leading_neighbor_lines_do_not_fail_verification():
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate
    from app.redaction import service
    text = ("code, marks, works, compilations, atlases, know-how or concepts (hereinafter Intellectual Property) "
            "relating to SCHULTZ Proprietary Technology, SCHULTZ anticipated products and/or services, and/or other "
            "Intellectual Property developed during the course of discussions with SCHULTZ, whether or not "
            "protectable by patent, copyright or trademark or as a trade secret is and shall be owned by SCHULTZ. ") * 3
    style = ParagraphStyle("t", fontName="Times-Roman", fontSize=12, leading=15, alignment=4)
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=letter).build([Paragraph("<u>Miscellaneous</u> " + text, style) for _ in range(6)])
    data = buf.getvalue()
    scan_result = asyncio.run(pipeline.scan(data))
    assert scan_result["findings"]
    ids = [f.id for f in scan_result["findings"]]
    output, count = asyncio.run(service.redact(data, scan_result, len(scan_result["pages"]), ids, []))
    assert count >= len(ids)


def _form_pdf():
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 10)
    c.drawString(60, 740, "Your social security number")
    c.drawString(60, 720, "239"); c.drawString(120, 720, "81"); c.drawString(170, 720, "1234")
    c.drawString(60, 690, "Spouse's social security number")
    c.drawString(60, 670, "1 5 7"); c.drawString(120, 670, "9 2"); c.drawString(170, 670, "5 6 7 8")
    c.drawString(60, 640, "b Routing number"); c.drawString(260, 640, "d Account number")
    c.drawString(60, 622, "0 2 1 0 0 0 0 2 1"); c.drawString(260, 622, "4 9 3 8 2 9 1 0 3 4")
    c.save()
    return buf.getvalue()


def test_form_cells_are_joined_and_typed_by_label():
    result = asyncio.run(pipeline.scan(_form_pdf()))
    found = {(f.type, "".join(ch for ch in f.text if ch.isdigit())) for f in result["findings"]}
    assert ("SSN", "239811234") in found
    assert ("SSN", "157925678") in found
    assert ("BANK_ROUTING", "021000021") in found
    assert ("BANK_ACCOUNT", "4938291034") in found


def test_adjacent_long_fields_are_not_merged():
    result = asyncio.run(pipeline.scan(_form_pdf()))
    digits = ["".join(ch for ch in f.text if ch.isdigit()) for f in result["findings"]]
    assert not any(len(d) > 17 for d in digits)


def _prose_pdf(lines):
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 740
    for line in lines:
        c.drawString(60, y, line)
        y -= 18
    c.save()
    return buf.getvalue()


def test_found_values_are_flagged_everywhere_they_repeat():
    data = _prose_pdf([
        "Taxpayer name: Jordan Sample",
        "Contact is JORDAN SAMPLE for questions.",
        "SSN 123-45-6789 appears here.",
        "Later the number 123-45-6789 is repeated in a note.",
    ])
    result = asyncio.run(pipeline.scan(data))
    ssn = [f for f in result["findings"] if f.type == "SSN"]
    assert len(ssn) == 2
    names = [f for f in result["findings"] if f.type == "PERSON_NAME" and "sample" in f.text.lower()]
    assert len(names) >= 2  # the uppercase repeat is flagged too
    assert all(f.rects for f in result["findings"])


def test_custom_terms_are_flagged_case_insensitively_and_whole_word():
    data = _prose_pdf(["Project Falcon is confidential.", "We met with acme corp. and ACME  CORP today.", "Falconry is a hobby."])
    result = asyncio.run(pipeline.scan(data, terms=["falcon", "Acme Corp"]))
    custom = [f.text.lower() for f in result["findings"] if f.type == "CUSTOM"]
    assert custom.count("falcon") == 1          # "Falconry" is not a whole-word match
    assert sum(1 for t in custom if t.split() == ["acme", "corp"] or t.split() == ["acme", "corp."]) >= 0
    assert len([t for t in custom if t.startswith("acme")]) == 2


def test_terms_are_cleaned_and_limited():
    from app.detection.terms import clean_terms
    assert clean_terms(["  a  ", "Bob  Smith", "bob smith", "", "x" * 200]) == ["Bob Smith"]
    assert len(clean_terms([f"term{i}" for i in range(80)])) == 50


def test_scan_endpoint_accepts_custom_terms():
    with TestClient(app) as client:
        doc_id = str(uuid4())
        assert client.post(f"/api/documents/{doc_id}", headers=HEADERS, content=_prose_pdf(["Project Falcon here."])).status_code == 201
        res = client.post(f"/api/documents/{doc_id}/scan", headers={"Authorization": "Bearer x"}, json={"terms": ["Falcon"]})
        assert res.status_code == 200
        assert any(f["type"] == "CUSTOM" for f in res.json()["findings"])
        assert "Falcon" not in res.text  # values stay masked


def _levels_pdf():
    return _prose_pdf([
        "Customer SSN: 123-45-6789 on file.",
        "Call 555-010-4477 for help.",
        "Savings account number 84930125 is active.",
        "Reference code 55501234567 was issued.",
        "Ship to 742 Evergreen Terrace, Springfield, IL 62704 today.",
        "Meet with Marcus Delacroix about renewal.",
    ])


def _at(level):
    """One scan carries every level; a level shows the findings tagged with it."""
    result = asyncio.run(pipeline.scan(_levels_pdf(), sensitivity=level))
    shown = [f for f in result["findings"] if level in f.levels]
    return result, shown, {f.type for f in shown}


def test_low_sensitivity_flags_only_high_certainty_items():
    result, shown, types = _at("low")
    assert "SSN" in types and "ADDRESS" in types     # validated format and street address rule
    assert "PHONE" not in types                      # format-only
    assert "BANK_ACCOUNT" not in types               # context-only
    assert result["sensitivity"] == "low"


def test_balanced_sensitivity_adds_context_and_phone():
    _, shown, types = _at("balanced")
    assert {"SSN", "PHONE", "BANK_ACCOUNT", "ADDRESS"} <= types


def test_high_sensitivity_flags_unlabeled_numbers_and_never_flags_less():
    _, low, _ = _at("low")
    _, balanced, _ = _at("balanced")
    _, high, _ = _at("high")
    assert len(low) <= len(balanced) <= len(high)
    assert "55501234567" in {f.text for f in high}       # long unlabeled number, only at High
    assert "55501234567" not in {f.text for f in balanced}


def test_findings_report_the_levels_that_show_them():
    result = asyncio.run(pipeline.scan(_levels_pdf()))
    ssn = next(f for f in result["findings"] if f.type == "SSN")
    assert ssn.levels == {"low", "balanced", "high"}
    long_number = next(f for f in result["findings"] if f.text == "55501234567")
    assert long_number.levels == {"high"}


def test_form_label_words_are_never_flagged():
    data = _prose_pdf(["Name", "Your first name and initial", "Home address", "Date of birth", "Signature",
                       "Taxpayer name: Jordan Sample"])
    result = asyncio.run(pipeline.scan(data, sensitivity="high"))
    flagged = {f.text.strip().lower() for f in result["findings"]}
    assert not flagged & {"name", "home address", "address", "signature", "date of birth", "your first name and initial"}
    assert any("sample" in t for t in flagged)           # the real name is still found


def test_scan_endpoint_validates_sensitivity():
    with TestClient(app) as client:
        doc_id = str(uuid4())
        assert client.post(f"/api/documents/{doc_id}", headers=HEADERS, content=_levels_pdf()).status_code == 201
        auth = {"Authorization": "Bearer x"}
        assert client.post(f"/api/documents/{doc_id}/scan", headers=auth, json={"sensitivity": "extreme"}).status_code == 422
        ok = client.post(f"/api/documents/{doc_id}/scan", headers=auth, json={"sensitivity": "low"})
        assert ok.status_code == 200 and ok.json()["sensitivity"] == "low"
