"""Authenticate requests using Firebase, never a client-supplied UID."""
from functools import lru_cache
from typing import Annotated

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.exceptions import DefaultCredentialsError

from app.config import FIREBASE_PROJECT_ID

bearer = HTTPBearer(auto_error=False)

@lru_cache(maxsize=1)
def firebase_app() -> firebase_admin.App:
    if not FIREBASE_PROJECT_ID:
        raise ValueError("Firebase project ID is not configured")
    return firebase_admin.initialize_app(
        credentials.ApplicationDefault(),
        {"projectId": FIREBASE_PROJECT_ID},
        name="redact-me-backend",
    )

def require_user(
    authorization: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict:
    if authorization is None or authorization.scheme.lower() != "bearer":
        raise HTTPException(401, "Sign in to access this endpoint.",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        # Checks issuer, audience, signature, expiry, revocation and disabled accounts.
        return auth.verify_id_token(
            authorization.credentials, app=firebase_app(), check_revoked=True
        )
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError,
            auth.RevokedIdTokenError, auth.UserDisabledError):
        raise HTTPException(401, "Your session is invalid or expired. Sign in again.",
                            headers={"WWW-Authenticate": "Bearer"}) from None
    except (DefaultCredentialsError, OSError):
        raise HTTPException(503, "Firebase backend credentials are not configured.") from None
    except ValueError:
        raise HTTPException(401, "Unable to validate your session.",
                            headers={"WWW-Authenticate": "Bearer"}) from None
    except Exception:
        # Do not expose token contents, credential paths, or SDK stack traces.
        raise HTTPException(503, "Authentication service is unavailable. Try again later.") from None
