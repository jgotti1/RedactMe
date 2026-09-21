"""Synthetic PDFs only. Validate rejection, isolation and temporary lifecycle."""
import asyncio
from uuid import uuid4

import pymupdf
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from firebase_admin import auth

from app.main import app
from app.documents.store import store
from app.documents import routes

HEADERS = {"Authorization": "Bearer synthetic-token", "Content-Type": "application/pdf"}


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    store.clear()
    monkeypatch.setattr("app.auth.firebase.firebase_app", lambda: object())
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", lambda *a, **k: {"uid": "one", "email_verified": True})
    yield
    store.clear()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def pdf(pages=1, encrypted=False):
    with pymupdf.open() as doc:
        for _ in range(pages):
            doc.new_page().insert_text((72, 72), "Synthetic document")
        return doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="test-only") if encrypted else doc.tobytes()


def upload(client, data=None, headers=None):
    key = str(uuid4())
    response = client.post('/api/documents/' + key, content=pdf() if data is None else data, headers=HEADERS if headers is None else headers)
    return key, response


def test_valid_upload_status_delete(client):
    key, result = upload(client)
    assert result.status_code == 201
    assert result.json()["status"] == "VALIDATED"
    assert result.json()["page_count"] == 1
    assert result.json()["size_bytes"] > 0
    assert result.headers['cache-control'] == 'no-store'
    assert client.get('/api/documents/' + key, headers=HEADERS).status_code == 200
    item = store.documents[key]
    assert client.delete('/api/documents/' + key, headers=HEADERS).status_code == 204
    assert not item.data and not store.documents
    assert client.get('/api/documents/' + key, headers=HEADERS).status_code == 404


@pytest.mark.parametrize('body', [b'', b'not a pdf', b'%PDF-1.7\nnot a document\n%%EOF'])
def test_invalid_rejected_and_discarded(client, body):
    _, result = upload(client, body)
    assert result.status_code in (413, 422)
    assert not store.documents and not store.active
    assert 'not a document' not in result.text


def test_truncated_pdf_rejected(client):
    _, result = upload(client, pdf()[:-20])
    assert result.status_code == 422 and not store.documents


def test_encrypted_pdf_rejected(client):
    _, result = upload(client, pdf(encrypted=True))
    assert result.status_code == 422
    assert 'Password-protected' in result.text
    assert not store.documents


def test_page_limit(client):
    _, result = upload(client, pdf(pages=201))
    assert result.status_code == 422 and not store.documents


def test_size_limit_counted_stream(client, monkeypatch):
    monkeypatch.setattr(routes, 'MAX_BYTES', 100)
    # False Content-Length cannot bypass counted streaming.
    _, result = upload(client, pdf(), {**HEADERS, 'Content-Length': '1'})
    assert result.status_code == 413 and not store.documents


def test_wrong_mime(client):
    _, result = upload(client, headers={**HEADERS, 'Content-Type': 'text/plain'})
    assert result.status_code == 415 and not store.documents


def test_auth_required_before_body(client):
    _, result = upload(client, headers={'Content-Type': 'application/pdf'})
    assert result.status_code == 401 and not store.documents


def test_unverified_email_rejected(client, monkeypatch):
    monkeypatch.setattr('app.auth.firebase.auth.verify_id_token', lambda *a, **k: {'uid': 'one', 'email_verified': False})
    _, result = upload(client)
    assert result.status_code == 403 and not store.documents


@pytest.mark.parametrize('error', [auth.InvalidIdTokenError('invalid'), auth.RevokedIdTokenError('revoked'), auth.UserDisabledError('disabled')])
def test_bad_sessions_rejected(client, monkeypatch, error):
    def reject(*a, **k):
        raise error
    monkeypatch.setattr('app.auth.firebase.auth.verify_id_token', reject)
    _, result = upload(client)
    assert result.status_code == 401 and not store.documents


def test_owner_isolation(client, monkeypatch):
    key, _ = upload(client)
    monkeypatch.setattr('app.auth.firebase.auth.verify_id_token', lambda *a, **k: {'uid': 'two', 'email_verified': True})
    assert client.get('/api/documents/' + key, headers=HEADERS).status_code == 404
    assert client.delete('/api/documents/' + key, headers=HEADERS).status_code == 204
    assert key in store.documents


def test_replacement_and_invalid_replacement(client):
    key, _ = upload(client)
    first = store.documents[key]
    second, result = upload(client)
    assert result.status_code == 201 and key not in store.documents and not first.data
    _, result = upload(client, b'bad')
    assert result.status_code == 422 and second not in store.documents


def test_expiration_clears_bytes(client):
    key, _ = upload(client)
    item = store.documents[key]
    item.deadline = 0
    store.expire()
    assert not item.data and not store.documents


def test_shutdown_clears_bytes():
    with TestClient(app) as client:
        key, _ = upload(client)
        item = store.documents[key]
    assert not item.data and not store.documents


def test_validation_failure_cleanup(client, monkeypatch):
    async def fail(data):
        raise HTTPException(422, 'PDF validation timed out. The upload was discarded.')
    monkeypatch.setattr(routes, 'validate_pdf', fail)
    _, result = upload(client)
    assert result.status_code == 422 and not store.documents and not store.active


def test_cancel_before_upload(client):
    key = str(uuid4())
    client.delete('/api/documents/' + key, headers=HEADERS)
    result = client.post('/api/documents/' + key, content=pdf(), headers=HEADERS)
    assert result.status_code == 409 and not store.documents


def test_cancel_during_validation(client, monkeypatch):
    async def cancelled(data):
        for key in list(store.documents):
            store.cancel(key, 'one')
        return 1
    monkeypatch.setattr(routes, 'validate_pdf', cancelled)
    _, result = upload(client)
    assert result.status_code == 409 and not store.documents and not store.active


def test_capacity_is_bounded(client, monkeypatch):
    monkeypatch.setattr('app.documents.store.MAX_DOCUMENTS', 0)
    _, result = upload(client)
    assert result.status_code == 503 and not store.documents


def test_busy_owner_rejected(client):
    store.active.add('one')
    _, result = upload(client)
    assert result.status_code == 429


def test_cors_upload_delete(client):
    for method in ['POST', 'DELETE']:
        result = client.options('/api/documents/' + str(uuid4()), headers={
            'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': method,
            'Access-Control-Request-Headers': 'authorization,content-type'})
        assert result.status_code == 200

@pytest.mark.parametrize('body, message', [
    (b'', 'empty (0 bytes)'),
    (b'\x89PNG\r\n\x1a\nsynthetic', 'appears to be an image'),
    (b'\xff\xd8\xffsynthetic', 'appears to be an image'),
    (b'This is a text file', 'does not contain a PDF header'),
    (b'%PDF-1.7\ntruncated', 'corrupted or incomplete'),
])
def test_specific_invalid_file_messages_and_cleanup(client, body, message):
    _, response = upload(client, body)
    assert response.status_code == 422
    assert message in response.json()['detail']
    assert not store.documents and not store.active


def test_blank_pdf_has_clear_error(client):
    with pymupdf.open() as document:
        document.new_page()
        document.new_page()
        body = document.tobytes()
    _, response = upload(client, body)
    assert response.status_code == 422
    assert 'all pages appear empty' in response.json()['detail']
    assert not store.documents


def test_blank_page_with_populated_page_is_valid(client):
    with pymupdf.open() as document:
        document.new_page()
        document.new_page().insert_text((72, 72), 'Synthetic content')
        body = document.tobytes()
    _, response = upload(client, body)
    assert response.status_code == 201 and response.json()['page_count'] == 2


def test_image_inside_pdf_is_supported(client):
    with pymupdf.open() as source:
        source.new_page().insert_text((72, 72), 'Scanned document example')
        image = source[0].get_pixmap()
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_image(page.rect, pixmap=image)
        body = document.tobytes()
    _, response = upload(client, body)
    assert response.status_code == 201
