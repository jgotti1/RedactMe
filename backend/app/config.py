"""Load backend-only configuration from the project root."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "").strip()
FRONTEND_ORIGINS = [origin.strip() for origin in os.getenv(
    "FRONTEND_ORIGINS", "http://localhost:5173"
).split(",") if origin.strip()]
# An empty template value should not override Application Default Credentials.
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip():
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
