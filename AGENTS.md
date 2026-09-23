# Redact Me — shared project instructions and tracking

## Master specification and planning reference

Read [PLANNING.md](PLANNING.md) before planning or implementing features. It contains the full user-provided master application specification, setup notes and approved amendments. Use it alongside this file to preserve the intended scope and requirements. Apply later explicit user instructions and approved amendments when they change an earlier requirement.

Read [PHASE_2_PLANNING.md](PHASE_2_PLANNING.md) before planning or implementing administration, persistent usage tracking, account entitlements, trials, subscriptions, billing or payment-provider integration. It is a tracked, secret-free draft plan; its unresolved product decisions must be confirmed before implementation.

PLANNING.md is a local, Git-ignored file containing secrets. Never print, copy, log or commit its secret values. Read the specification and setup information without exposing credentials. If the file is missing in a fresh checkout, request the specification before implementing features that depend on it.

## Stack and current scope
- HTML/CSS/vanilla JavaScript with Vite for development and bundling. No frontend framework without user approval.
- Python/FastAPI backend; Firebase Authentication owns all login credentials.
- Current authorized implementation: Google and email/password signup/login, password reset, email verification controls, an authenticated backend greeting, and a signed-in document workspace preview.
- AGENTS.md is the shared source of truth for Codex and Claude instructions, architectural decisions, progress and remaining work. Update this file so both tools use the same context. Read README.md for setup commands. PLANNING.md is a local ignored specification containing secrets; never print or commit its secret section.
- Keep AGENTS.md current automatically as coding progresses; do not wait for the user to ask. Before completing each coding task, record relevant scope and behavior changes, decisions, validation results and remaining work, and reconcile outdated status statements. Never include secrets or sensitive user data.
- No third-party AI service is used (OpenAI removed September 21, 2026). Never place backend secrets in VITE_* variables.
- Document stack: PyMuPDF, Microsoft Presidio, deterministic rules, modular Tesseract OCR. No OpenAI or other external AI.

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
- OpenAI project was created earlier but is no longer used by the app.
- Firebase project: redactme-15625; registered web app.
- Google and Email/Password providers enabled; localhost authorized.

## Remaining setup
- Implement production frontend serving through FastAPI, same-origin API calls, and a Railway build/start configuration when authorized.
- Local Firebase service-account JSON supplied by the user in backend/; root .env now points to it via GOOGLE_APPLICATION_CREDENTIALS. The file is Git-ignored; never display its contents.
- Complete a real Google login and verify the greeting against Firebase once credentials are configured.
- The OpenAI key was deleted from the local `.env` and from the local PLANNING.md on September 21, 2026. The user should still revoke it in the OpenAI dashboard because it was shared in chat.
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
- Frontend: Start scan calls the endpoint; findings render in the review panel (superseded: review is now interactive, see the Redaction section).
- Tesseract is installed (see OCR section).

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
- Next: step 2 onward in "Next steps" (real review selections and page previews). Step 1 (OCR) is done for detection; scanned-page redaction/rebuild remains in step 5.

## Redaction, verification and download (Phases 10-15) — September 21, 2026
- Implemented end to end for the signed-in workspace: page previews (`GET /api/documents/{id}/pages/{n}/preview`, rendered in a subprocess), selectable findings with overlay boxes, manual drawn redaction areas, `POST /api/documents/{id}/redact`, and single-use `GET /api/documents/{id}/download`.
- Redaction (`backend/app/redaction/redactor.py`, subprocess): PyMuPDF `add_redact_annot` + `apply_redactions` (removes text, image pixels, touched vector art; not overlays); scanned/mixed pages are rasterized and rebuilt as image-only pages (original OCR text layer dropped); output is rewritten fresh with metadata, XMP, embedded files, JavaScript, thumbnails, annotations, links and bookmarks removed. Finding rectangles come only from the server; client manual rectangles are bounds-validated.
- Mandatory verification (`service.verify`): output re-extracted (re-OCR if needed); page count matches; no metadata/annotations/embedded files; native pages have no words inside redacted rectangles; rebuilt pixel pages have solid-black redacted regions (`region_check.py`, >=98% dark; OCR misreads black bars as text so words are not used there); distinctive value types (SSN, EIN, account, routing, card, email, phone, ID, DOB) are rechecked. Selected-area, pixel, sanitization and integrity failures always block download. A separate occurrence outside selected areas can proceed only through the explicit, scoped keep-visible acknowledgment described below.
- Download is single use: after sending, original, output and findings are purged; also purged on delete/expiry. Uses attachment disposition and no-store.
- UI: review view with page navigation, keep/reject checkboxes, "Add manual redaction" drag-to-draw (click a drawn box to remove), "Approve & redact", "Download PDF" (enabled only after verification), "Discard document".
- Validation: 48 backend tests (fictional tax return: redaction removes SSNs/accounts, unselected text preserved, single-use download, failed verification blocks download, cross-user 404, scanned-page rebuild) and frontend build pass. The new review UI has not been exercised in a real browser session (needs a signed-in Firebase user); do that next.

## UI refinements after first review — September 21, 2026
- Choose PDF and Start scan share one large, bold, centered style (`#choose-pdf, #start-scan`); Approve & redact is larger; the download button is wider (min 250px, no wrapping; full width on phones).
- Errors from Approve & redact also show under the button (`#review-note`); download errors show in the download panel.
- When verification passes the download panel is highlighted (green border, glow, scrolled into view) and shows this warning: once downloaded, the temporary copy is permanently deleted from the server and cannot be downloaded again, so the user should save it securely.
- Download filename is the original name plus `_redacted` before `.pdf` (e.g. `tax_return_redacted.pdf`), sanitized. After a successful download the same button becomes "Finish and start a new document" (clears the workspace); Approve/manual buttons are disabled. The blob stays in the browser tab with a "save it again from this page" link until the user finishes, because the server copy is already deleted.
- `.gitignore`: `documents/` (private document folders) would have ignored `backend/app/documents/`; exception `!backend/app/documents/` added.

## Remaining work (current)
1. Real signed-in browser QA of the full flow, including manual drawing on real pages, scanned PDFs and download.
2. Hardening (Phase 16): rate limits, concurrency and memory caps per user, fuzz/adversarial PDFs, dependency pinning, security headers/CSP.
3. Production static serving through FastAPI, relative API base, Railway config (Phase 17); authorize the Railway host in Firebase.
4. Email/support phase (SUPPORT_EMAIL, EMAIL_API_KEY) not started.

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
- Options panel layout: widened to 330px to match the review panel (290 to 270px on narrower screens; stacks above the document at 900px and below), with larger 14px option text, 18px checkboxes and bold 13px group headings (Identity, Contact, Financial, Other) with an underline rule.
- While a document is in review (`.workspace-grid.reviewing`, set by `review.js`), the options panel is hidden and the document area spans its column too, giving the page preview about double the width. The panel returns when the review ends (finish, discard or reset). Saved option choices still apply to the hidden panel; to change them, finish or discard the document. (At 900px and below the layout is unchanged: the panel is simply hidden.)

## Session lifetime — September 21, 2026
- Firebase Auth now uses in-memory persistence (`frontend/js/firebase.js`, `initializeAuth` with `inMemoryPersistence` and the popup resolver), so a page refresh or closed tab signs the user out; sessions are no longer restored from browser storage.
- `frontend/js/main.js` also signs out after 15 minutes without pointer/keyboard/scroll/touch activity and after an absolute 8 hours, showing a notice on the login page. Sign-out disposes the workspace, which discards the temporary server upload.
- Verified: build passes and Firebase initializes in headless Chrome. Real login, refresh sign-out and idle timeout still need a manual check with a signed-in browser. Limits are constants `IDLE_LIMIT_MS` and `SESSION_LIMIT_MS` in main.js.
- Changes are local and uncommitted per the user's standing instruction.

## Larger working area and approved state — September 21, 2026
- Layout: `.workspace` max-width 1640px, the document section and download panel scaled with CSS `zoom: 1.25`, review/options panels `zoom: 1.12`, roomier gaps and upload box. Zoom is disabled at 1100px and below to keep small screens usable. Chrome, Safari and current Firefox support `zoom`.
- After a successful Approve & redact, the button turns grey, is disabled and reads "PDF ready to download below ↓". Changing any selection, option or manual area re-enables it as "Approve & redact" and blocks the download until re-approved. Finish/discard resets it.
- Verified with a headless Chrome screenshot and stubbed API. Changes are local and uncommitted per the user's instruction.

## OpenAI removed — September 21, 2026
- User decision: the app no longer uses OpenAI (added cost and complexity for little benefit). Removed `backend/app/detection/openai_service.py`, the `openai` dependency, the `use_ai` scan option and `ai_status` response field, the "AI" finding source, the "Other sensitive details" (AI-only) redaction option, the "Skip AI verification" checkbox and tooltip, "Powered by OpenAI" footer text, AI wording on the landing page, and the OpenAI test mocks.
- Detection is now local only: deterministic rules with checksums, Presidio (spaCy) and Tesseract OCR. A scan is `complete` when every page was analyzed (scanned/low-confidence OCR pages are flagged, never reported as clean). Contextual details that only an AI would catch (for example a partial account number without a clear label) rely on the rules and manual redaction.
- PLANNING.md (local specification) still describes OpenAI in its general prose; the key value and key variable examples were removed. Treat this decision as an approved amendment that supersedes it. Privacy copy no longer needs to mention third-party AI processing; documents are processed only on our server.
- 57 backend tests and the frontend build pass. Changes are local and uncommitted per the user's instruction.

## Form-cell detection and all-pages-reviewed gate — September 21, 2026
- Bug: SSNs and bank numbers on IRS-style forms were missed. PyMuPDF puts each boxed cell on its own text line (for example "239\n81\n1234", or one digit per cell), so single-line regexes never matched. `rules._digit_runs` now rejoins short digit-only cell lines (each 4 digits or fewer) and space-separated digit tokens into runs, then types each run by the nearest preceding label within 120 characters: Social Security (validated area/group/serial), routing (ABA checksum), or account (4-17 digits). Long adjacent fields (routing above account) are never merged. The SSN regex also now accepts newlines between groups. Tests: `test_form_cells_are_joined_and_typed_by_label`, `test_adjacent_long_fields_are_not_merged` (59 backend tests pass).
- Limits: detection needs a nearby label word (social/SSN, routing, account) for form cells; unlabeled digit boxes and unusual layouts need manual redaction. Scanned forms depend on OCR reading order.
- Review gate: Approve & redact stays disabled until every page has been displayed in the preview (a page counts once its image renders). The page label shows "Page N of M · X of M reviewed" and the note explains what is missing. UI-only gate; `review.js` `reviewed` set.
- Verified in headless Chrome with a 3-page stub (button enabled only after page 3 rendered). Changes are local and uncommitted per the user's instruction.
- Page navigation now also has "First" and "Last" buttons (disabled on the first/last page). Jumping only marks the pages actually displayed as reviewed, so the all-pages-reviewed gate still requires visiting every page.

## Better name coverage — September 21, 2026
- Problem: some names were redacted and others not. Names come from Presidio/spaCy NER, which is probabilistic and weak on isolated form text, ALL CAPS and unusual names, and the AI step was removed.
- Changes: (1) `en_core_web_md` replaces `en_core_web_sm` when installed (falls back to sm); it is pinned in `requirements.txt` as a wheel URL. (2) `detect/terms.py` `propagate`: every value found once is flagged at all other occurrences (case-insensitive, whitespace-flexible, whole-word), and full person names also propagate their individual parts (3+ letters), marked source `REPEAT`. (3) Custom terms: a "Your custom terms" box in the options panel (one per line or comma-separated, saved per account in `localStorage` key `redactme.customTerms.v1.<uid>`) is sent with the scan (`POST /scan` JSON `{terms}`, max 50, 2-100 chars); matches are case-insensitive whole words, type `CUSTOM`, source `CUSTOM`. Terms apply at scan time, so rescan after changing them.
- Review list now shows friendly source names (Pattern check, Name/entity model, Your term, Repeat of a found value). 63 backend tests pass; headless Chrome verified terms save, restore and send. Not done: lowering the name confidence threshold (would add false positives). Changes are local and uncommitted per the user's instruction.

## Detection sensitivity — September 21, 2026
- New Low / Balanced (default) / High control at the top of the options panel (saved per account in `localStorage` key `redactme.sensitivity.v1.<uid>`), sent with each scan as `sensitivity` in the `POST /scan` JSON body (validated to low|balanced|high). Changing it requires a rescan. The review banner reports the level used.
- Profiles live in `backend/app/detection/sensitivity.py`. Low: name confidence >= 0.8, no place-name model, other entities >= 0.6, no phone/EIN pattern rules, only checksum-style routing and validated SSN cell runs, no label-based account/DOB/ID rules, repeats of the full value only. Balanced: today's behavior (names >= 0.6, places >= 0.6, other >= 0.4, label-based rules, name-part repeats of 3+ letters). High: names >= 0.4, places >= 0.4, other >= 0.3, unlabeled nine-digit (valid SSN shape) and 8-17 digit numbers flagged, capitalized word pairs that look like names (with a stoplist), name-part repeats of 2+ letters.
- New street-address rule (all levels) so Low still catches full street addresses without the place-name model.
- Bug fixed along the way: the label lookback for inline numbers crossed lines, so an "account" label on an earlier line could label an unrelated number. Inline numbers now use labels on their own line only; form-cell numbers (digits alone on their lines) still look up to 120 characters above.
- 67 backend tests pass (new tests cover each level, endpoint validation). Headless Chrome verified default, selection, persistence, and that the scan request carries the level. Changes are local and uncommitted per the user's instruction.

## Form labels, live sensitivity slider and sticky review panel — September 21, 2026
- Bug: generic form label words such as "Name" or "Home address" were flagged. `backend/app/detection/labels.py` drops PERSON_NAME/ADDRESS candidates whose words are all generic label words (custom terms are exempt); a real name next to a label is still found. Test: `test_form_label_words_are_never_flagged`.
- Live sensitivity: one scan now computes every level (`pipeline.scan` runs rules and merge/propagation for low, balanced and high; Presidio runs once via `analyze` then `select` applies each level's thresholds). Each finding carries `levels`; the API returns them. A Low-Balanced-High slider above the page preview switches the level instantly with no rescan; selections follow visibility (items that drop out are deselected, new ones start selected), the download is invalidated, and the suggestion count is shown. The left-panel level is the starting position and the scan request's `sensitivity` is echoed back. The slider is disabled while redacting and after download.
- Review usability: Approve & redact was hard to find because the review panel stretched to the full height of the tall page preview. While reviewing, the panel is now sticky (top 10px, scrolls internally) with the action buttons pinned to its bottom; verified by measurement in headless Chrome (approve button stays in the viewport at any scroll). The panel is static on narrow screens. Added "Go to next unviewed page" under the notes, and the note lists which pages are still unviewed (the all-pages-reviewed gate is unchanged).
- Tests: 69 backend tests pass; frontend build passes. Verified slider behavior with a stubbed API in headless Chrome. Changes are local and uncommitted per the user's instruction.

## Review controls hardening — September 21, 2026
- Sensitivity: the live control now has clickable Low / Balanced / High buttons in addition to the drag slider, and reacts to both `input` and `change`; failures show a message instead of failing silently. Verified with a real mouse drag (Chrome remote debugging) through low, high, low, high, low on a 19-page, 1000+ finding scan, plus button and change-event paths. A user-reported "stops working after high then low" could not be reproduced; if it recurs, capture the browser console.
- Approve gate clarity: while pages remain unviewed the button reads "Review all pages first (X of N)" and the note under it is an amber box listing unviewed pages; "Go to next unviewed page" jumps to the next one. Reaching the last page alone (for example with the Last button) does not unlock approval; every page must be displayed.
- Decision change (supersedes the hard gate above): Approve is no longer blocked before every page is viewed. While pages remain unviewed the button is yellow and reads "Approve without full review (X of N viewed)"; clicking it shows a confirm warning that the user is redacting blindly. Once all pages are viewed it turns green and reads "Approve & redact". Server-side selected-area, pixel, sanitization and integrity verification remains mandatory; later amendments add a scoped acknowledgment only for a separate sensitive occurrence intentionally kept visible.
- Page navigation toolbar in the review view now wraps instead of clipping, stays sticky at the top, and greys out disabled buttons.

## Publication checkpoint — September 21, 2026
- User authorized committing and pushing all current tracked changes, including the staged new detection modules. This supersedes the earlier notes to keep these changes local and uncommitted.
- Includes removal of external AI, improved local detection and custom terms, sensitivity controls, and review/navigation refinements described above.
- Pre-publication validation: all 69 backend tests and the frontend production build passed; staged files checked against known local secrets and credential patterns, with no matches. Private environment files, credentials and PLANNING.md remain excluded.


## Splash screen design and privacy copy — September 21, 2026
- User authorized committing and pushing the splash changes and accompanying RedactMe branding updates; this supersedes earlier instructions to leave this work uncommitted.
- Enlarged the complete brand block and aligned its left edge with the privacy notice. Raised the desktop login card and aligned its right edge with the privacy badge text; smaller screens retain responsive spacing. The header badge sits at the title's top line.
- Added a 3% darker splash background, refined card styling and document preview, and enlarged supporting labels and footer by 2 px. Privacy notice is offset down by 8 px plus 3 CSS mm.
- Final notice: “Keep sensitive documents out of public AI chats.” Followed by: “Review, approve, and download your redacted file—without sending it to public AI services. Working files are deleted after download, keeping the process simple and helping protect your privacy.”
- Replaced the misleading “Runs locally” preview badge with “You’re in control.” Processing uses the backend; cleanup follows download, and the browser retains the re-save copy until the user finishes. No guarantee of secure memory erasure is implied.
- Standardized visible branding as RedactMe, including sign-in form modes, page titles and options text. Authentication and document processing behavior are unchanged.
- Validation: frontend production build and diff whitespace check passed. Earlier desktop Chrome checks verified placement; full mobile visual QA remains pending. Backend code is unchanged.
- Publication scope: AGENTS.md, frontend/index.html, frontend/css/styles.css, frontend/js/main.js and frontend/js/redaction-options.js. Private configuration and credentials remain excluded.

## Workspace background and workflow alignment — September 21, 2026
- Signed-in workspace now shares the splash screen's gradient and 3% darker background tint.
- Centered the three workflow steps within their equal-width columns; mobile numbers and labels are centered too. Workflow behavior is unchanged.
- Frontend production build passed. These follow-up changes are local and uncommitted.

## Workspace brand alignment and step connectors — September 21, 2026
- Aligned the signed-in brand block with the options panel by matching header insets to the workspace at desktop and mobile breakpoints. Added 12 px of top breathing room.
- Added muted connecting rules between workflow groups; mobile rules connect the numbered circles without crossing labels. Splash positioning and workflow behavior are unchanged.
- Frontend production build and diff whitespace check passed. Changes remain local and uncommitted; live signed-in visual QA remains pending.

## Larger workspace status and account details — September 21, 2026
- Increased the screenshot-highlighted account/sign-out text, Workspace preview label, workflow titles, subtitles and step numbers by 2 px. Enlarged the numbered circles from 33 to 37 px and added slightly more status-bar padding.
- Kept mobile typography proportional and adjusted connecting-rule positions for the larger circles.
- Frontend production build passed. Changes remain local and uncommitted.

## Compact workspace introduction in header — September 21, 2026
- Removed the Workspace preview label and box. Moved the document-workspace introduction into the top-right header above the account name and sign-out button, using smaller heading sizing and right alignment to fit beside the brand.
- Removed the former introduction row from the workspace and reduced top padding so the workflow and document panels move upward. Header wraps on smaller screens; the introduction is hidden along with signed-out account controls. The workspace heading's existing focus target is preserved.
- Frontend production build and diff whitespace check passed. Live signed-in visual QA remains pending. Changes remain local and uncommitted.

## Account controls above introduction — September 21, 2026
- Reordered the signed-in header so the account name and sign-out button appear above the introduction block, matching visual and DOM order. Supersedes the previous introduction-above-account arrangement.
- Frontend production build passed. Changes remain local and uncommitted.

## Introduction between brand and account — September 21, 2026
- Moved the desktop workspace introduction into the open header space between the brand and account controls, following the user's annotated screenshot. Introduction is left-aligned; account controls remain at the far top right. Smaller screens retain the stacked header.
- Supersedes the desktop introduction-below-account layout. Frontend production build and diff whitespace check passed; live signed-in visual QA remains pending.
- Committed and pushed September 21, 2026 with workspace background and workflow alignment changes.

## Workspace background and workflow centering — September 21, 2026
- Signed-in workspace now shares the splash screen's gradient background (radial gradient with 3% darker overlay tint); matches login page appearance.
- Centered the three workflow steps (1-2-3 status bar) horizontally on the page; step indicators and labels are centered within each column. Mobile layout also centers elements.
- Moved workspace introduction heading from inside the content area to the header, positioned between the brand and account controls.
- Frontend production build passed. Committed and pushed as `73b11f3` with the message "Match workspace background to splash screen and center workflow status bar."

## Workspace header layout refinement — September 21, 2026
- Reorganized the signed-in header for improved visual hierarchy and professionalism.
- Repositioned the workspace introduction heading (DOCUMENT WORKSPACE / "A little less visible. A lot more private.") to the top-right of the header.
- Account controls (user name and Sign out button) now stack vertically directly below the heading, maintaining right alignment.
- All elements are right-aligned with consistent spacing; mobile layout remains responsive with centered elements.
- Frontend production build passed. Committed and pushed.

## Approval flow fix — September 21, 2026
- Fixed "Approve without full review" button: was blocked by disabled state check in click handler.
- Changed logic to check only if already busy, calculate approval state locally, show confirmation only if pages not fully reviewed, and proceed with redaction after user confirms.
- Now button works as intended: displays warning dialog for unreviewed pages, and clicking OK proceeds with redaction exactly like normal "Approve & redact" after full review.
- Committed `c15ed00`.

## Verification temporarily disabled — September 21, 2026 (superseded September 22, 2026)
- Post-redaction verification was temporarily bypassed after the old approved-value check produced an unlocatable false positive. This bypass is no longer active; see "Verification re-enabled and value matcher rewritten" below.

## Review panel button layout refinement — September 21, 2026
- Redesigned review actions for professional appearance and clear visual hierarchy.
- Secondary buttons (Add manual redaction, Go to next unviewed) now display side-by-side at top in compact size.
- Primary action "Approve & redact" is full-width, green, and clearly dominant.
- Partial approval state (not all pages reviewed): button remains green with subtle opacity instead of jarring yellow.
- Discard & start over: small text link at bottom, understated and out of primary workflow.
- Result: Clean, professional layout with one clear primary action and supporting secondary actions tucked away. Committed `eadbe0a`.

## Add manual redaction button styling — September 21, 2026
- Added `.outline` CSS class for tertiary button actions: white background, dark green border (#4a6155), dark text (#1a2524), subtle hover state.
- Changed "Add manual redaction" button from `.secondary` to `.outline` class for more professional, refined appearance.
- Result: Clear visual hierarchy with primary action (green), secondary action (white, light border), and tertiary action (white, dark border) distinct from each other. Frontend build passes.

## Login/splash page layout swap and polish — September 22, 2026
- Swapped the login page's two-column layout: the sign-in card is now on the left (`grid-template-columns` and `order` on `.intro`/`.login-column` in `frontend/css/styles.css`), marketing/intro content on the right. Previously the card was on the right.
- Removed a stale pixel-tuned hack (`-30mm` vertical lift plus a horizontal `left: calc(...)` offset) that was positioning the card correctly only when it sat on the right; with the swap it was dragging the card up over the brand logo. No longer needed with the new left-column placement.
- Fixed a real pre-existing mobile bug: `.site-header .privacy-note { max-width: 780px }` had no media query and silently overrode the mobile-sized widths at every viewport. Scoped it under `max-width: 700px`. Also added `min-width: 0` to flex/grid items (`main > *`, `.brand-block`, `.site-header`) to prevent "blowout" (content-sized children forcing a track wider than the viewport).
- Verified layout with zero horizontal overflow from 320px to 1240px+ using Chrome DevTools Protocol directly (`Emulation.setDeviceMetricsOverride` + `document.documentElement.scrollWidth`), after discovering `chrome --headless --window-size=W --screenshot` does not reliably produce an accurate W-px CSS viewport in this environment — that flag gave false-positive overflow readings; CDP emulation is the reliable way to check this page's layout going forward.
- De-cluttered the card's helper text: `.auth-note` and the `#status` live region both say near-identical "sign in with X" messages; restyled `.status` to drop its boxed/bordered callout look (was `border-left` + `min-height: 42px`, read like an orphaned blockquote) into one quiet centered line under `.auth-note`. All existing text kept, per user instruction — this was a styling change only.
- Reduced dead whitespace at the bottom of the card: `.card-bottom` (the "Built around privacy and human review" line) now has a subtle top border and tighter spacing instead of a large empty gap.
- Per user's follow-up sketch: card enlarged (padding 28×32 → 40×44) and pushed down (`margin-top: 56px` on `.login-column`, `≥701px` only), while the intro/marketing text moved up to sit closer under the header badge (`padding-top: 6px` on `.intro`). Mobile (`<701px`, single-column stacked layout) is unaffected by this repositioning.
- Validation: `npm run build` passes; layout checked at 320/375/390/480/699/700/701/1000/1101/1280px via CDP-driven screenshots, no overflow, no clipping.

## Login splash redesign — September 22, 2026
- Reworked the signed-out page into a compact product header, left-side value/privacy story and right-side authentication card. Reduced the oversized masthead, removed the warning-style privacy banner from the header, strengthened typography and spacing, and simplified the visual hierarchy while preserving all Firebase authentication controls and element IDs.
- Added an in-context privacy assurance, clearer identify/review/redact steps and responsive styling. The illustrative document preview remains desktop-only; mobile prioritizes the product message and sign-in card.
- Frontend production build passes. Browser QA passed at desktop and 390px mobile widths with no horizontal overflow or browser errors; login, signup and reset behavior was not changed.

## Signed-in workspace redesign — September 22, 2026
- Reframed the signed-in page as a focused document workbench while preserving every existing workflow state and control. The shared header is compact in the authenticated state, the three-step status bar is now a distinct orientation card, and the document canvas has clearer visual priority over the supporting preferences and review rails.
- Restyled the preferences, upload, review, findings, active-review and download surfaces with consistent spacing, typography, borders, states and responsive behavior. Preferences remain fully available; they become a single stacked panel on mobile and still hide during real document review so the PDF canvas can expand.
- Frontend production build passes. Browser QA covered the empty upload state, fictional sample review, expanded active-review layout, 1536px desktop and 390px mobile; no horizontal overflow or browser errors were found. No authentication, upload, scan, selection, redaction, workflow or download behavior changed.

## Verification re-enabled and value matcher rewritten — September 22, 2026
- Restored mandatory post-redaction `service.verify`; downloads are fail-closed again when the output cannot be proven safe.
- Replaced whole-page alphanumeric normalization and substring counting, which could concatenate unrelated neighboring text into a false match. Distinctive approved values now use boundary-aware, formatting-tolerant matching, page-scoped allowances for deliberately unselected duplicate occurrences, and a maximum three-character separator between value characters.
- Verification failures now identify the page and, for remaining approved values, the safe category (for example bank account number) without returning the sensitive value. Pixel verification also returns the page containing the least-dark selected region.
- Added regression coverage for formatted values, form-cell line breaks, longer-number substring collisions, unrelated intervening words, deliberately unselected duplicate occurrences, and safe page/category error reporting.
- User-directed recovery: when a distinctive sensitive value remains outside every selected redaction area, the API returns a page/category warning and an opaque one-time token. The UI offers either return-to-review or an explicit "keep this occurrence visible" confirmation. The token is bound to the exact selection plan and temporary document; changing selections invalidates all acknowledgments. Each acknowledged occurrence is counted separately. The output is regenerated and all selected-area, pixel, sanitization, page-integrity and OCR checks rerun; none of those checks can be bypassed. Successful exceptions return `VERIFIED_WITH_RETAINED_DATA` and remain visibly disclosed in the review and download copy.
- All 72 backend tests and the frontend production build pass. Tests cover the one-time acknowledgment flow and confirm downloads stay blocked before acknowledgment; the first sandboxed run encountered only a local tldextract cache permission issue and passed when rerun with normal cache access.
- Manual QA fixture generated locally at `output/pdf/redactme_verification_warning_test.pdf` (ignored by Git). At Balanced sensitivity it yields exactly one SSN suggestion; selecting that suggestion and approving produces the intended page 1 / SSN keep-visible warning because the same fictional digits also appear in a slash-formatted line outside the selected area. Rendering and the real scan/redaction warning path were verified.
- Replaced the browser's ambiguous OK/Cancel prompt for this warning with an accessible in-app decision dialog. It identifies the page and sensitive-data category, focuses the safe default, and offers explicit actions: “Return to review” or “Keep visible & continue.” Dismissing the dialog or pressing Escape returns to review and releases no file. Frontend production build passes; browser QA verified both decisions, Escape handling, focus, desktop layout and 390px mobile layout with no horizontal overflow.
- Follow-up dialog sizing: reduced the warning to a compact 456px near-square card with tighter content spacing. Both decision buttons stay side by side and right-aligned on desktop; they remain side by side in a two-column action row on small screens instead of stacking vertically. Frontend production build passes; browser screenshots verified the compact desktop and 390px mobile layouts with no clipping.
- Warning-card visual follow-up: strengthened the card boundary with a muted green-gray rule and separated the centered, side-by-side actions into a lightly tinted footer. The footer remains full-bleed inside the rounded card at desktop and mobile widths. Frontend production build passes; browser screenshots verified desktop and 390px mobile rendering.
- Increased the warning card's outer rule from 2px to 3px for clearer separation from the dimmed document behind it; color and all dialog behavior remain unchanged. Frontend production build passes, and browser-computed styling confirms the 3px rule.

## Verified download dialog — September 22, 2026
- A successful redaction/verification now opens a compact success dialog matching the retained-data warning's visual language. It summarizes verification, discloses any intentionally retained sensitive occurrences, repeats the single-use server-download warning, and offers “Return to review” or “Download PDF.” If dismissed, an enabled “Open verified download” review action reopens it without re-running redaction.
- Browsers cannot confirm that a user completed the OS save action. After the authenticated PDF response is received and the browser download is started, the dialog truthfully changes to “Download started” and asks the user to confirm the file appears in downloads. It provides an in-tab “Save PDF again” recovery link and a clear primary “Clear workspace & continue” action. Clearing revokes the in-tab copy through the existing workspace teardown; the server copy has already been deleted by the single-use endpoint.
- Frontend production build passes. Browser QA used stubbed preview, redaction and PDF responses to exercise the full verified-ready → download-started → clear-workspace sequence. It confirmed the recovery link, dialog cleanup and review reset; desktop and 390px mobile screenshots show no clipping or overflow.
- Follow-up: removed the now-redundant full-width download footer and its dead styles/DOM dependencies. The success dialog content is centered as a balanced vertical composition. Dismissing it changes the review action to an enabled “Open verified download” button, so users can reopen the modal without re-running redaction. Browser QA verified dismiss/reopen, download, recovery and clear-workspace behavior on desktop and 390px mobile; the frontend build passes.
- Final download confirmation now has a prominent 5px green rule plus a subtle outer ring. Its recovery notice uses clearer language and a separately displayed heading: the server copy was securely removed, the user should confirm the PDF is saved locally, “Save PDF again” is available if needed, and clearing also removes the browser-tab recovery copy.

## Railway deployment prep — September 23, 2026
- Implemented production serving: FastAPI serves `frontend/dist` (`/assets` mount plus SPA fallback for routes like `/app`, registered last so `/api/*` wins; unknown `/api/*` still 404s). `frontend/js/api.js` now uses relative same-origin paths in production builds (`import.meta.env.DEV` keeps the `127.0.0.1:8000` default for local dev).
- Firebase credentials: optional `FIREBASE_CREDENTIALS_JSON` runtime secret (service-account JSON contents) used via `credentials.Certificate`; falls back to Application Default Credentials/`GOOGLE_APPLICATION_CREDENTIALS` locally.
- Added multi-stage `Dockerfile` (Node build stage taking public `VITE_FIREBASE_*` build args; Python 3.12 runtime with `tesseract-ocr`, non-root user, single uvicorn worker on `$PORT`), `.dockerignore` (excludes env files, credentials, PLANNING, PDFs, tests) and `railway.json` (Dockerfile builder, `/api/health` healthcheck, one replica). Documents are in process memory, so never scale beyond one worker/replica.
- Railway runtime variables: `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_JSON`, `FRONTEND_ORIGINS` (the Railway domain), plus build-time `VITE_FIREBASE_API_KEY/AUTH_DOMAIN/PROJECT_ID/APP_ID`. The Railway domain must be added to Firebase authorized domains.
- Validation: frontend build and all 72 backend tests pass; TestClient confirmed `/`, `/app`, `/api/health` and unknown `/api/*` behavior. Docker image not yet built; no Railway deployment has occurred yet.
