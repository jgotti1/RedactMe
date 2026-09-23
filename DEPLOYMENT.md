# RedactMe deployment reference (Railway + Bluehost)

Secret-free notes from the first deploy on September 23, 2026. Never paste secret values here.

## Architecture
One Railway service builds the `Dockerfile` (Vite build stage, then Python 3.12 + Tesseract). FastAPI serves the built frontend and `/api/*` from one origin. Config lives in `railway.json` (Dockerfile builder, `/api/health` healthcheck, 1 replica).

## Railway resources
- Project `redactme`, environment `production`, service `redactme`, source GitHub `jgotti1/RedactMe` branch `main` (pushes to `main` redeploy).
- Default domain: `redactme-production.up.railway.app`
- Custom domain: `redactme.margotticode.com` (see DNS below)

## Variables (service `redactme`)
| Name | Kind | Notes |
|---|---|---|
| `FIREBASE_PROJECT_ID` | runtime | `redactme-15625` |
| `FIREBASE_CREDENTIALS_JSON` | runtime SECRET | full contents of the Firebase service-account JSON. Paste it into the Railway dashboard yourself (`pbcopy < backend/<key file>.json`); never through chat or Git |
| `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID` | build-time, public | web config; the Dockerfile declares them as `ARG`s so Railway passes them into the Vite build |
| `VITE_API_BASE_URL` | leave unset | production uses relative `/api` paths |

Variables added in the dashboard can be **staged**: they are not live until you click **Deploy** on the staged-changes banner. Check with the variables list before assuming they applied.

## Bluehost subdomain
1. Railway service, Settings, Networking, add custom domain `redactme.margotticode.com` (done via the MCP; it returns the CNAME target).
2. Bluehost, Domains, `margotticode.com`, DNS, Add Record: **Type** CNAME, **Host** `redactme` (subdomain only), **Points to** the Railway target (currently `ogvt2y4p.up.railway.app`; re-read it from Railway if in doubt), default TTL. Remove any existing `redactme` A/CNAME record first.
3. Wait for propagation (minutes to about an hour); Railway then issues the HTTPS certificate automatically.
4. Firebase Console, Authentication, Settings, Authorized domains: add `redactme.margotticode.com` (keep the `up.railway.app` entry).

## Firebase checklist for any new hostname
Add it under Authorized domains, otherwise Google sign-in fails on that host.

## Operational gotchas
- **Documents live in process memory.** Run exactly one worker and one replica. Any redeploy, restart or crash discards every in-flight upload; users must re-upload. During a redeploy the old and new containers overlap for roughly 10 seconds, so avoid deploying while someone is mid-document. (First deploy: an upload made during that window returned 404 on `/redact`; a fresh upload after the redeploy settled was the fix.)
- Uploads expire 15 minutes after upload (`TTL_SECONDS` in `backend/app/documents/store.py`).
- Trial plan memory may be tight for OCR/Presidio; check the service metrics if a deploy is OOM-killed and move to the Hobby plan.
- Useful checks: `https://<domain>/api/health`, Railway deploy and HTTP logs, service metrics.

## Local commands
`npm run dev` (frontend, port 5173), `npm run dev:backend` (backend, port 8000), `npm run build`, `npm run test:backend`.
