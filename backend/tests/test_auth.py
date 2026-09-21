import pytest
from fastapi.testclient import TestClient
from firebase_admin import auth
from google.auth.exceptions import DefaultCredentialsError
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def firebase_stub(monkeypatch):
    monkeypatch.setattr("app.auth.firebase.firebase_app", lambda: object())

def test_public_health():
    assert client.get("/api/health").json() == {"status": "ok"}

@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic anything"}])
def test_missing_bearer_rejected(headers):
    assert client.get("/api/hello", headers=headers).status_code == 401

@pytest.mark.parametrize("error", [
    auth.InvalidIdTokenError("invalid"),
    auth.ExpiredIdTokenError("expired", None),
    auth.RevokedIdTokenError("revoked"),
    auth.UserDisabledError("disabled"),
])
def test_invalid_sessions_rejected(monkeypatch, error):
    def reject(*args, **kwargs):
        raise error
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", reject)
    response = client.get("/api/hello", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 401
    assert "fake-token" not in response.text

def test_verified_token_returns_greeting(monkeypatch):
    def verify(token, *, app, check_revoked):
        assert token == "synthetic-token"
        assert check_revoked is True
        return {"uid": "synthetic-user"}
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", verify)
    response = client.get("/api/hello", headers={"Authorization": "Bearer synthetic-token"})
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from the backend"}
    assert response.headers["cache-control"] == "no-store"

def test_missing_credentials_fail_closed(monkeypatch):
    def missing():
        raise DefaultCredentialsError("private-path")
    monkeypatch.setattr("app.auth.firebase.firebase_app", missing)
    response = client.get("/api/hello", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 503
    assert "private-path" not in response.text

def test_cors_allows_frontend_only():
    headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
               "Access-Control-Request-Headers": "authorization"}
    assert client.options("/api/hello", headers=headers).status_code == 200
    headers["Origin"] = "https://untrusted.example"
    assert client.options("/api/hello", headers=headers).status_code == 400
