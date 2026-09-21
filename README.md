# Redact Me

Google or email/password sign-in opens the document workspace at `/app`. The workspace includes upload, review and download areas plus an interactive fictional sample. Real PDF processing is not implemented yet.

## Structure

- `frontend/`: HTML, CSS and vanilla JavaScript, Firebase web SDK, Vite.
- `backend/`: Python/FastAPI and Firebase Admin SDK.
- `AGENTS.md`: shared instructions, architecture, progress and remaining work for Codex and Claude.
- `CLAUDE.md`: directs Claude to read and follow `AGENTS.md`.
- `PLANNING.md`: local specification, ignored by Git because it contains secrets.

## Deployment architecture — approved September 18, 2026

- Deploy the complete application to Railway as a single Python/FastAPI service under one HTTPS domain.
- Keep separate `frontend/` and `backend/` source folders.
- Build the HTML/CSS/vanilla JavaScript frontend with Vite; FastAPI serves the resulting static assets and HTML pages alongside `/api/*` endpoints.
- Backend-served frontend means serving the built files; it does not require a frontend framework or dynamic server-side HTML templates.
- Production frontend requests use relative same-origin API paths, such as `/api/hello`. Separate frontend/API CORS is unnecessary in production; local development may continue using separate servers.
- Build frontend assets during deployment; run the Python service on Railway’s assigned port. Keep API routing distinct from static-file routing.
- Firebase remains the authentication provider. Authorize the Railway hostname and any custom app domain in Firebase before production login.
- Backend secrets are runtime configuration and must never enter frontend bundles or container images.
- Process documents in memory or isolated temporary storage with explicit expiration and cleanup across upload, review, redaction and download. Do not rely on deploy/restart filesystem deletion as cleanup; do not attach persistent storage for PDFs.
- This is the chosen deployment architecture. Production static serving, relative API configuration and Railway deployment configuration still need implementation; no deployment has occurred.

## Install

Node.js 20+ and Python 3.10+ are recommended. The frontend uses Vite 6, compatible with the installed Node.js 20.17.

```sh
npm --prefix frontend install
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
```

Local `.env` files have been created and remain private. On a fresh checkout, create a root `.env` with `FIREBASE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS` and `FRONTEND_ORIGINS`. Create `frontend/.env` with `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID` and `VITE_API_BASE_URL`. Get the Firebase web configuration from Project settings → General → Your apps; use `http://127.0.0.1:8000` for the local API URL. Only public configuration may use `VITE_*` names. Environment example files are intentionally omitted.

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

Open **http://localhost:5173** and sign in with Google or email. Firebase authentication opens the workspace at `/app`; sign-out returns to `/`. The workspace preserves email verification controls and includes a sample review with selectable fictional findings. Upload, manual redaction, approval and download controls are disabled until secure document processing is implemented.

The login page no longer calls the backend greeting or displays connection-testing controls. The protected `/api/hello` endpoint remains available for backend authentication checks. Client-side workspace routing is a UI convenience; all future document endpoints must independently verify Firebase tokens. Vite serves `/app` during development. Production SPA fallback routing remains part of the planned FastAPI static-serving work.

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

## Email accounts

Use the email form to sign in, or select Create an account to register with a confirmed password. New email accounts receive a Firebase verification email; the signed-in panel supports sending another email and refreshing verification status. Forgot password opens the reset form. Passwords are handled by Firebase and are never sent to our API or stored by the application. The workspace preview and backend greeting currently permit authenticated unverified email accounts; future document endpoints must define and enforce their verification policy on the backend.

Real Firebase signup/login and email delivery require testing with your own account. Reference: [Firebase email/password authentication](https://firebase.google.com/docs/auth/web/password-auth) and [verification and password reset](https://firebase.google.com/docs/auth/web/manage-users).
