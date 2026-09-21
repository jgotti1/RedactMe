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
Upload validation, detection, OCR, review, manual/true redaction, verification and single-use download exist (see below). No email support or deployment yet.
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

## Detection and review (Phases 5, 6, 8, 9, 10 read-only) — September 21, 2026
- User approved all remaining phases. `POST /api/documents/{id}/scan` runs `backend/app/detection/`: subprocess PyMuPDF extraction (words + boxes), page classification (NATIVE_TEXT/SCANNED_IMAGE/MIXED/EMPTY), deterministic rules with checksums (SSN, EIN, card/Luhn, routing/ABA, email, phone, context-based account/DOB/ID), Presidio (spaCy en_core_web_sm), and OpenAI Structured Outputs (`openai_service.py`, default model `gpt-5-nano`, override with OPENAI_MODEL; AI_ANALYSIS=off disables). Findings are merged/deduplicated per page with line rectangles.
- AI output is untrusted: schema-enforced, values must appear verbatim on the reported page or are discarded. Raw values stay server-side (in the temporary document); the API returns masked values, type, level, sources, reason and rects only. No content or exceptions are logged.
- Fail closed: `complete` is true only if every page was analyzed and OpenAI succeeded. Pages that are scanned/mixed are listed as unanalyzed (OCR not built). The UI shows "Nothing in this PDF looks to need redaction" only for a complete scan with zero findings; otherwise it says the result is incomplete.
- Scan has a "Skip AI verification" checkbox (default unchecked, sends `use_ai=false`; ai_status `user_skipped`, still marked complete because it is the user's explicit choice, with the UI noting only local checks ran).
- Frontend: Start scan calls the endpoint; findings render in the review panel (superseded: review is now interactive, see the Redaction section).
- Tests: `backend/tests/test_scan.py` (OpenAI mocked) with a fictional tax return generated by `tests/make_sample_tax_return.py`. All 41 backend tests and the frontend build pass.
- Live OpenAI verification: still BLOCKED at last check (`credit_balance_exhausted` for the key in `.env`; user reports credits were added). Confirm the credits belong to the same organization/project as the key, then rerun a live scan on the fictional sample (expect the AI to add "ending in 4931").
- Tesseract is installed (see OCR section).
- Remaining: see the end of this file. Privacy copy must state that extracted text is sent to OpenAI.
- The skip checkbox has an ⓘ tooltip explaining that AI verification sends extracted text to OpenAI and that skipping keeps analysis on our server (less thorough).

## Next steps to complete redaction and download (steps 1-8 now implemented; see later sections)
1. **OCR (Phase 7):** after `sudo xcodebuild -license accept` and `brew install tesseract`, add a modular OCR engine for SCANNED_IMAGE/MIXED pages returning text, boxes and confidence; run the same detectors on OCR text; flag low-confidence pages for manual review. Then unanalyzed pages no longer block a complete scan.
2. **Review UI (Phase 10):** make selections real (keep/reject per finding, select all), render page previews with PDF.js highlights from returned rects, and send only finding IDs back to the server; raw values never go to the frontend.
3. **Manual redaction (Phase 11):** draw/select areas or text on the preview; send page + rects; validate bounds server-side; include them in the approved set.
4. **True redaction (Phase 12):** on approval, apply PyMuPDF redactions (`add_redact_annot` + `apply_redactions` removing text and image pixels) to the approved findings/rects, in a sandboxed subprocess on the in-memory copy; never use overlays only.
5. **Scanned pages (Phase 13):** rasterize scanned pages, blank redacted pixels, rebuild the page as an image, and drop the original OCR text layer.
6. **Sanitize output (Phase 14):** strip metadata, XMP, attachments, annotations, embedded files, bookmarks, JavaScript, hidden layers and incremental-save history; write a fresh PDF.
7. **Verification (Phase 14, mandatory):** re-extract text from the output (and re-OCR scanned pages), confirm no approved value remains, page count and unredacted content are intact; fail closed and block download on any uncertainty.
8. **Download and cleanup (Phase 15):** authenticated, single-use, short-lived `GET /api/documents/{id}/download` only after verification passes, with `Content-Disposition` attachment and no-store; purge original, redacted output and findings on download, cancel, failure and expiry.
9. **Hardening and tests (Phase 16):** tests for each step using the fictional tax return, including failed verification blocking download, cross-user access, and expiry; then Railway deployment (Phase 17) with production static serving and updated privacy copy.

## OCR (Phase 7) — September 21, 2026
- Tesseract installed (Homebrew). `backend/app/detection/ocr_runner.py` is a modular, sandbox-style subprocess: renders SCANNED_IMAGE/MIXED pages at 200 DPI, pipes the PNG to Tesseract over stdin (no document pixels on disk) and returns word boxes (PDF points) with confidence. OCR words replace native words on those pages; pages classify from native text. Mean confidence below 60 or an OCR failure leaves the page unanalyzed, so the scan is reported incomplete. Cap of 40 OCR pages per scan.
- Backend tests: 43 pass, including a scanned-page OCR + SSN detection test (skipped if Tesseract is missing).
- Live OpenAI still returned `credit_balance_exhausted` at last check; user says credits are being added. Re-run the live AI verification on the fictional sample afterward.
- Next: step 2 onward in "Next steps" (real review selections and page previews). Step 1 (OCR) is done for detection; scanned-page redaction/rebuild remains in step 5.

## Redaction, verification and download (Phases 10-15) — September 21, 2026
- Implemented end to end for the signed-in workspace: page previews (`GET /api/documents/{id}/pages/{n}/preview`, rendered in a subprocess), selectable findings with overlay boxes, manual drawn redaction areas, `POST /api/documents/{id}/redact`, and single-use `GET /api/documents/{id}/download`.
- Redaction (`backend/app/redaction/redactor.py`, subprocess): PyMuPDF `add_redact_annot` + `apply_redactions` (removes text, image pixels, touched vector art; not overlays); scanned/mixed pages are rasterized and rebuilt as image-only pages (original OCR text layer dropped); output is rewritten fresh with metadata, XMP, embedded files, JavaScript, thumbnails, annotations, links and bookmarks removed. Finding rectangles come only from the server; client manual rectangles are bounds-validated.
- Mandatory verification (`service.verify`): output re-extracted (re-OCR if needed); page count matches; no metadata/annotations/embedded files; native pages have no words inside redacted rectangles; rebuilt pixel pages have solid-black redacted regions (`region_check.py`, >=98% dark; OCR misreads black bars as text so words are not used there); distinctive value types (SSN, EIN, account, routing, card, email, phone, ID, DOB) must not reappear in the text. Any failure or uncertainty returns 422, keeps the output unreleased and blocks download.
- Download is single use: after sending, original, output and findings are purged; also purged on delete/expiry. Uses attachment disposition and no-store.
- UI: review view with page navigation, keep/reject checkboxes, "Add manual redaction" drag-to-draw (click a drawn box to remove), "Approve & redact", "Download PDF" (enabled only after verification), "Discard document".
- Validation: 48 backend tests (fictional tax return: redaction removes SSNs/accounts, unselected text preserved, single-use download, failed verification blocks download, cross-user 404, scanned-page rebuild) and frontend build pass. The new review UI has not been exercised in a real browser session (needs a signed-in Firebase user); do that next.
- Still remaining: browser QA of the review/manual-draw/download flow, live OpenAI verification once credits apply, broader hardening (rate limits, fuzzing), Railway deployment, updated privacy copy.

## UI refinements after first review — September 21, 2026
- Choose PDF and Start scan share one large, bold, centered style (`#choose-pdf, #start-scan`); Approve & redact is larger; the download button is wider (min 250px, no wrapping; full width on phones).
- Errors from Approve & redact also show under the button (`#review-note`); download errors show in the download panel.
- When verification passes the download panel is highlighted (green border, glow, scrolled into view) and shows this warning: once downloaded, the temporary copy is permanently deleted from the server and cannot be downloaded again, so the user should save it securely.
- Download filename is the original name plus `_redacted` before `.pdf` (e.g. `tax_return_redacted.pdf`), sanitized. After a successful download the same button becomes "Finish and start a new document" (clears the workspace); Approve/manual buttons are disabled. The blob stays in the browser tab with a "save it again from this page" link until the user finishes, because the server copy is already deleted.
- Scan option "Skip AI verification" (default unchecked) has an information tooltip about sending extracted text to OpenAI.
- `.gitignore`: `documents/` (private document folders) would have ignored `backend/app/documents/`; exception `!backend/app/documents/` added.
- Headless Chrome with stubbed API responses was used to verify scan, approve and download click flows; a real signed-in browser pass with live Firebase and OpenAI is still pending.

## Remaining work (current)
1. Real signed-in browser QA of the full flow, including manual drawing on real pages, scanned PDFs and download.
2. Live OpenAI verification once credits apply to this key/project; consider the review of AI confidence copy (advisory only).
3. Hardening (Phase 16): rate limits, concurrency and memory caps per user, fuzz/adversarial PDFs, dependency pinning, security headers/CSP.
4. Production static serving through FastAPI, relative API base, Railway config (Phase 17); authorize the Railway host in Firebase.
5. Privacy copy across the app must state that extracted text is sent to OpenAI unless AI verification is skipped.
6. Email/support phase (SUPPORT_EMAIL, EMAIL_API_KEY) not started.

## Multi-page review and validation fixes — September 21, 2026
- Review findings and the count badge now show only the displayed page; selections and manual areas remain associated with their pages, and approval submits the full document selection. The summary explicitly states the document-wide selection count.
- Page navigation cancels stale preview requests and hides the old page until the correct image loads. Manual drawing is blocked while previews load or redaction runs; selection changes invalidate the previous downloadable result.
- Optimized pixel verification to copy each rendered page's sample buffer once instead of once per row. Fixed image extraction shadowing document-level metadata information, preserving mandatory sanitization verification.
- Upload failures now distinguish images masquerading as PDFs, empty files, missing PDF headers, corrupt/incomplete PDFs, no-page/blank PDFs, encryption and size/page limits. Valid image-based/scanned PDFs and populated PDFs containing blank pages remain supported. Rejected uploads are discarded.
- Redaction errors report safe verification reasons without document content; failed/uncertain verification continues to block download.
- Validation: all 59 backend tests and frontend production build passed, including multi-page native/scanned redaction and specific invalid-upload errors. Synthetic browser review confirms page-specific findings, selections retained across navigation, and multi-page approval reaching verified download with no browser errors. The user's original failing PDF has not been reproduced; user is retrying and can provide the new specific error if it persists.

## Verification false-positive fix and progress indicator — September 21, 2026
- Bug: approving redaction on a dense contract failed with "Content remains inside a selected redaction area" because verification counted any remaining word whose bounding box overlapped a redacted line by >0.5pt; tightly spaced lines have overlapping word boxes. Verification now counts a leftover word only when its center lies inside a redacted rectangle. Regression test: `test_tight_leading_neighbor_lines_do_not_fail_verification`. 60 backend tests pass.
- Approve & redact now shows a spinner and "Redacting & verifying…"; the download panel turns amber with a moving progress bar and a "please keep this page open" note while working, and points to the error message if verification blocks the file.
- Note: other editors (Codex or the user) also changed `routes.py`, `review.js` (page-scoped finding list, `invalidateDownload`) and the validator during this session; changes were merged in place, not overwritten.

## Live workflow status and Discard & start over — September 21, 2026
- The three-step strip at the top (`frontend/js/workflow.js`, `setWorkflow`) now tracks progress: step 1 shows upload/validation and "PDF ready", step 2 covers scanning and "Choose what to redact", step 3 covers "Redacting & verifying…", "Verified. Ready to download" and "Downloaded and cleared". Finished steps show a check and green; the active step pulses while work runs; failures step back with a message. Finishing or discarding resets to step 1.
- Added "Discard & start over" beside Approve & redact (confirms first, then discards the server copy and resets the workspace). The existing "Discard document" link stays in the preview toolbar.
- Verified in headless Chrome with stubbed API responses through upload, scan, approve, download, finish and discard. Frontend build passes.

## Redaction options panel — September 21, 2026
- New left column "Redaction options" (`frontend/js/redaction-options.js`): grouped checkboxes for Names, Dates of birth, SSNs, ID numbers, Addresses, Phones, Emails, Bank accounts, Routing numbers, Card numbers, EINs and Other sensitive details. All default on; "Reset to defaults" restores them. Counts of detected items per type appear after a scan.
- Behavior: findings of an unchecked type are hidden from the review list and page overlay, removed from the selection, and never sent to the redact endpoint (the client sends only enabled finding IDs). Re-checking a type restores its recommended items. Toggling after verification invalidates the download until re-approved; options lock while redaction runs.
- Persistence: browser `localStorage` under `redactme.redactionOptions.v1.<uid>`, storing only the types turned OFF so future types default on. Storage access is isolated in `loadDisabled`/`saveDisabled` so it can move to a database later (per-user preference on the backend). Scanning still detects all types; only review/redaction is filtered.
- Verified in headless Chrome with stubbed API responses (uncheck phone: list 3 to 2, request body excluded it, storage written). Frontend build passes.
- Possible follow-ups: server-side enforcement of enabled types if preferences move to a database; option to skip AI for disabled types to save cost; per-document overrides.
- Options panel layout: widened to 330px to match the review panel (290 to 270px on narrower screens; stacks above the document at 900px and below), with larger 14px option text, 18px checkboxes and bold 13px group headings (Identity, Contact, Financial, Other) with an underline rule.
