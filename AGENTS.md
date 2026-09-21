# Redact Me — shared project instructions and tracking

## Master specification and planning reference

Read [PLANNING.md](PLANNING.md) before planning or implementing features. It contains the full user-provided master application specification, setup notes and approved amendments. Use it alongside this file to preserve the intended scope and requirements. Apply later explicit user instructions and approved amendments when they change an earlier requirement.

PLANNING.md is a local, Git-ignored file containing secrets. Never print, copy, log or commit its secret values. Read the specification and setup information without exposing credentials. If the file is missing in a fresh checkout, request the specification before implementing features that depend on it.

## Stack and current scope
- HTML/CSS/vanilla JavaScript with Vite for development and bundling. No frontend framework without user approval.
- Python/FastAPI backend; Firebase Authentication owns all login credentials.
- Current authorized implementation: Google and email/password signup/login, password reset, email verification controls, an authenticated backend greeting, and a signed-in document workspace preview.
- AGENTS.md is the shared source of truth for Codex and Claude instructions, architectural decisions, progress and remaining work. Update this file so both tools use the same context. Read README.md for setup commands. PLANNING.md is a local ignored specification containing secrets; never print or commit its secret section.
- Keep AGENTS.md current automatically as coding progresses; do not wait for the user to ask. Before completing each coding task, record relevant scope and behavior changes, decisions, validation results and remaining work, and reconcile outdated status statements. Never include secrets or sensitive user data.
- OpenAI calls must run only on the backend. Never place backend secrets in VITE_* variables.
- Future document stack: PyMuPDF, PDF.js, Microsoft Presidio, deterministic detection, modular OCR, OpenAI Structured Outputs.

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

## Security invariants
- Verify Firebase ID tokens on protected endpoints; never trust a client-supplied UID.
- Never commit secrets, local .env files, service-account JSON, or PLANNING.md.
- Never log PII, document contents, findings, passwords, or authentication tokens.
- No permanent PDF storage. Future document processing must have isolated temporary lifecycle and cleanup on success, cancellation and failure.
- Human review precedes redaction; support manual redactions and scanned/mixed PDFs.
- True redaction removes underlying text or pixels; overlays alone are forbidden.
- Remove original OCR layers when rebuilding scanned pages.
- Verification is mandatory; fail closed and block downloads if verification is uncertain or fails.
- Security must never be bypassed to fix functionality or make tests pass.
- Build incrementally. Do not add PDF processing or later phases without authorization.
- Update these instructions when architecture changes.

## Validation
- Frontend: npm run build
- Backend: npm run test:backend
- Test authentication failures and protected endpoints whenever security code changes.

## Implemented
- Separate frontend/ and backend/ folders.
- Vanilla JavaScript frontend with Firebase Google popup login, email/password signup and login, password reset, email verification controls, logout and automatic navigation to the workspace.
- FastAPI health endpoint and protected GET /api/hello returning Hello from the backend.
- Backend token verification with Firebase Admin SDK, including revocation and disabled-account checks.
- Git exclusions, backend authentication tests and development scripts.

## Setup confirmed by user
- OpenAI project created and funded.
- Firebase project: redactme-15625; registered web app.
- Google and Email/Password providers enabled; localhost authorized.

## Remaining setup
- Implement production frontend serving through FastAPI, same-origin API calls, and a Railway build/start configuration when authorized.
- Local Firebase service-account JSON supplied by the user in backend/; root .env now points to it via GOOGLE_APPLICATION_CREDENTIALS. The file is Git-ignored; never display its contents.
- Complete a real Google login and verify the greeting against Firebase once credentials are configured.
- Rotate the OpenAI key previously shared in chat before use. OpenAI is not called in this foundation.
- Choose an email provider during the account/support phase.

## Scope
No document uploads, detection, OCR, redaction, email support or deployment yet.
Never copy secrets into this tracked file. PLANNING.md is a local ignored reference.

## Public repository preparation — September 21, 2026
- Public GitHub repository: `jgotti1/RedactMe`; local `origin` points to it.
- Expanded Git exclusions for credentials and keys, private PDFs and document folders, temporary processing files, databases, logs, backups, archives and local editor/agent state.
- Removed both `.env.example` files at the user's request. All `.env.*` files are now ignored; README documents the required configuration variable names. Existing private `.env` files remain local.
- Checked publishable files and existing Git history against known local secret values and credential patterns; no matches found. Confirmed local environment files, planning reference and Firebase service-account JSON are ignored.
- Frontend production build and all 10 backend tests passed before preparing the project commit.
- Git ignore rules do not protect already tracked files or detect arbitrary secrets in source. Review staged changes before every public push.

## Validation completed
- Frontend production build passed.
- All 10 backend authentication/CORS tests passed with mocked Firebase verification.
- Browser check passed: page renders, Firebase initializes, Google button enabled, no browser errors.
- Live API: public health returns ok; unauthenticated greeting returns 401.
- Real Google login and greeting remain unverified until backend credentials are configured.
- Development servers started on localhost:5173 and 127.0.0.1:8000.

## Styling update — September 18, 2026
- Polished foundation page with consistent document/privacy branding, responsive layout and a decorative upcoming review preview.
- Added signed-in account presentation and backend connecting, success and error styles with accessible status updates.
- Organized FastAPI API documentation with service/workspace groups and request timing.
- Build and all 10 backend tests passed. Browser verified desktop and 390px mobile layouts, no horizontal overflow, no browser errors and enabled Google login. Greeting panel layout checked with placeholder content only; real Google login still awaits backend credentials.

## Firebase credential setup update
- Local service-account file validated for the expected project and excluded from Git.
- Restart the backend to load the updated .env; real authenticated greeting verification is still pending.

## Email authentication update
- Added email login, account creation with password confirmation and Firebase password-policy validation, password reset, and verification-email send/resend/check controls.
- Firebase manages passwords; no application password storage, custom password backend or logging added. Unverified email users can test the foundation greeting; document access policy must be enforced on the backend when document processing is implemented.
- Signup sends a Firebase verification email. Administrative signup notifications remain a future account/support task.
- Frontend build and all 10 backend tests passed. Browser checked form modes, password-mismatch blocking, mobile overflow and errors. Real email signup/login/reset and delivery have not been exercised against the live project.

## Workspace preview — September 21, 2026
- User authorized removal of login connection-testing UI and creation of the main document page only.
- Firebase sign-in/session restoration opens `/app`; sign-out and unauthenticated visits to `/app` return to `/`. Routing uses the existing vanilla JavaScript app and History API, with Vite's development fallback. Production static routing still needs implementation.
- Added responsive upload, review, and verified-download areas plus an explicitly fictional sample with selectable highlights. Real PDF upload, manual redaction, approval and download remain disabled; no document processing or storage added.
- Email signup, password reset and workspace verification controls remain. The protected backend greeting remains, but login no longer calls it.
- Frontend build and all 10 backend tests passed. Browser verified restored Firebase session navigation, sample selections, responsive layout, and sign-out. Real new signup and verification-email delivery were not exercised.

## Google sign-in branding — September 21, 2026
- Replaced the plain blue G with the standard multicolor Google G as an inline SVG and changed the button label to “Sign in with Google.” Firebase sign-in behavior is unchanged.
- Frontend production build passed.
