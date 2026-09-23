"""Authenticated workspace API with temporary PDF upload validation."""
import asyncio
from contextlib import asynccontextmanager, suppress

from app.documents.routes import router as documents_router
from app.documents.store import store
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.auth.firebase import require_user
from app.config import FRONTEND_DIST, FRONTEND_ORIGINS

@asynccontextmanager
async def lifespan(app):
    async def cleanup():
        while True:
            await asyncio.sleep(5)
            store.expire()
    task = asyncio.create_task(cleanup())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        store.clear()


app = FastAPI(
    lifespan=lifespan,
    title="Redact Me · Workspace API",
    description="Firebase-authenticated PDF upload and validation. Documents are temporary; scanning and redaction are not implemented.",
    version="0.1.0",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "displayRequestDuration": True},
    openapi_tags=[
        {"name": "Service", "description": "Public service availability."},
        {"name": "Documents", "description": "Temporary PDF validation; verified email required for upload."},
        {"name": "Workspace", "description": "Requires a verified Firebase ID token."},
    ],
)
app.add_middleware(
    CORSMiddleware, allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False, allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(documents_router)

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


# Production: serve the built frontend from the same origin. Registered last so /api/* routes win.
if (FRONTEND_DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (FRONTEND_DIST / path).resolve()
        if path and target.is_file() and FRONTEND_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")  # SPA routes such as /app
