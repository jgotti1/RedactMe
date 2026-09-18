# Redact Me

Foundation preview: Google sign-in followed by an authenticated Python API request displaying **Hello from the backend**.

## Structure

- `frontend/`: HTML, CSS and vanilla JavaScript, Firebase web SDK, Vite.
- `backend/`: Python/FastAPI and Firebase Admin SDK.
- `AGENTS.md`: permanent project instructions.
- `CLAUDE.md`: progress and remaining setup.
- `PLANNING.md`: local specification, ignored by Git because it contains secrets.

## Install

Node.js 20+ and Python 3.10+ are recommended. The frontend uses Vite 6, compatible with the installed Node.js 20.17.

```sh
npm --prefix frontend install
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
```

Local `.env` files have been created. On a fresh checkout, copy `.env.example` to `.env` and `frontend/.env.example` to `frontend/.env`. Fill the frontend template with the Firebase web configuration from Project settings → General → Your apps. Only public configuration may use `VITE_*` names.

## Firebase backend credentials

The frontend is already configured for `redactme-15625`. Google sign-in and localhost authorization must be enabled in the Firebase console.

For local backend authentication, use existing Application Default Credentials, or go to **Firebase Project settings → Service accounts → Firebase Admin SDK → Generate new private key**. Store that file privately, preferably outside the OneDrive project folder, and set its absolute path in the root `.env`:

```dotenv
GOOGLE_APPLICATION_CREDENTIALS=/absolute/private/path/service-account.json
```

Do not paste private-key JSON into chat or commit it. The backend checks revoked tokens and disabled accounts, so its credentials must have Firebase Authentication read access. Production should use an attached service identity instead of a downloaded key where possible.

## Run

In one terminal, from the project root:

```sh
npm run dev:backend
```

In another terminal:

```sh
npm run dev
```

Open **http://localhost:5173**, select **Continue with Google**, and sign in. The browser sends a Firebase ID token in the Authorization header to **http://127.0.0.1:8000/api/hello**. The API verifies it before returning the greeting. Sign out clears the displayed account and greeting. If credentials are missing, login can succeed but the protected API will show a setup error rather than bypass authentication.

`GET /api/health` is public. `GET /api/hello` requires authentication. CORS permits only `http://localhost:5173` by default; configure `FRONTEND_ORIGINS` as a comma-separated list for other frontend origins. Use HTTPS in production. Frontend builds do not include the root backend `.env`.

## Verify

```sh
npm run build
npm run test:backend
```

Backend tests use synthetic tokens and mocked Firebase verification. A real Google login requires your interaction and configured backend credentials.

## Current limits

No PDF processing or OpenAI requests are implemented. The root OpenAI key is reserved for a future backend phase and must be replaced before use because it was shared in chat. No passwords or documents are stored by this foundation.

References: [Firebase Google login](https://firebase.google.com/docs/auth/web/google-signin), [Firebase ID token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens), [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/), [Vite environment variables](https://vite.dev/guide/env-and-mode).
