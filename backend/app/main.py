"""Minimal authenticated API; no document processing yet."""
from typing import Annotated
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auth.firebase import require_user
from app.config import FRONTEND_ORIGINS

app = FastAPI(
    title="Redact Me · Workspace API",
    description="Foundation preview for Redact Me. Check service health, then sign in "
                "with Firebase to test the protected workspace greeting. "
                "Document processing is planned for a later phase.",
    version="0.1.0",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "displayRequestDuration": True},
    openapi_tags=[
        {"name": "Service", "description": "Public service availability."},
        {"name": "Workspace", "description": "Requires a verified Firebase ID token."},
    ],
)
app.add_middleware(
    CORSMiddleware, allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False, allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

class Greeting(BaseModel):
    message: str

@app.get("/api/health", tags=["Service"], summary="Check backend health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/api/hello", response_model=Greeting, tags=["Workspace"],
         summary="Get an authenticated greeting")
def hello(user: Annotated[dict, Depends(require_user)]) -> Greeting:
    return Greeting(message="Hello from the backend")
