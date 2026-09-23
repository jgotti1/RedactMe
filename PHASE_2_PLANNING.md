# RedactMe — Phase 2 Product Plan

Status: Draft for product review. No Phase 2 implementation is authorized by this document.

This plan covers the next business and administration phase after the secure document workflow: persistent user records, privacy-safe usage reporting, administrator controls, complimentary access, and paid subscriptions.

`PLANNING.md` remains the private master specification. This file contains no credentials or secret values.

## 1. Confirmed product direction

- Add an authenticated administrator page.
- Let administrators review user activity and aggregate usage.
- Let administrators activate or deactivate user accounts.
- Support an access override for users who should not be charged.
- Offer a three-day trial followed by a $19.99 USD monthly subscription.
- Preserve the existing privacy model: never persist PDFs, document contents, findings, redacted values, page images, filenames, or custom terms for administration or billing.

## 2. Decisions still requiring approval

- Payment provider. Stripe is recommended but not yet approved for implementation.
- Whether a payment card is required before the trial begins. Recommended: yes.
- Whether the trial is exactly 72 hours or ends at a calendar-day boundary. Recommended: exactly 72 hours.
- Trial usage allowance and paid-plan monthly limits.
- Grace period after a failed renewal. Recommended starting point: three days.
- Whether cancellation takes effect immediately or at the end of the trial/current paid period. Recommended: end of period.
- Whether sales tax is included in $19.99 or calculated at checkout.
- Email provider for trial-ending, failed-payment, and account-status notices.
- Retention periods for detailed usage events and administrative audit records.

## 3. Architectural principles

### 3.1 Separate identity, billing, and access

Do not represent every condition with one `active` flag. Evaluate three independent dimensions:

1. **Authentication status** — Firebase account enabled or disabled.
2. **Billing status** — no subscription, trialing, active, past due, canceled, unpaid, or paused.
3. **Access override** — none, complimentary, or internal.

This separation lets a person sign in to repair billing even when document processing is unavailable, and it allows complimentary access without creating a fake paid subscription.

### 3.2 Sources of truth

- Firebase Authentication: identity, email verification, administrator role, enabled/disabled login status, token revocation.
- Application PostgreSQL database: usage, subscription mirror, access overrides, webhook idempotency, and audit history.
- Payment provider: customer, subscription, invoice, and payment state.
- FastAPI: the only authority that combines these states and grants document-processing access.

### 3.3 No document persistence

Adding PostgreSQL does not change the document-security model. PDFs and derived document data remain in isolated temporary memory with the existing expiration and deletion lifecycle. The database stores operational counters only.

## 4. Access decision policy

Evaluate access on every protected document operation:

1. Reject an invalid, expired, revoked, or disabled Firebase identity.
2. Require verified email for document processing.
3. Allow an active internal or complimentary override.
4. Otherwise allow a subscription in `trialing` or `active` state.
5. Optionally allow `past_due` only until the configured grace-period deadline.
6. Deny document processing for all other billing states while still allowing account and billing management.

The browser may display access state, but it must never enforce or grant access by itself.

## 5. Administrator authorization

- Use a server-assigned Firebase custom claim such as `admin: true` for the coarse administrator role.
- Only a trusted server-side bootstrap process may grant or remove the claim.
- Every `/api/admin/*` endpoint must independently verify the Firebase token, revocation status, disabled status, verified email, and administrator claim.
- Prevent an administrator from deactivating their own account.
- Prevent removal or deactivation of the final administrator.
- Do not include permanent account deletion in the first release.
- Rate-limit administrative mutations and record every attempted change.
- Never expose password hashes, authentication tokens, payment credentials, or service credentials.

Custom-claim changes require a refreshed Firebase ID token. The admin bootstrap/runbook must account for that behavior.

## 6. Account activation and deactivation

Firebase remains authoritative for login status.

### Deactivate account

1. Confirm the acting administrator and target UID.
2. Reject self-deactivation and final-administrator deactivation.
3. Disable the Firebase user.
4. Revoke the user's refresh tokens.
5. Purge any temporary document owned by that UID.
6. Record an append-only audit event.
7. Return the status read back from Firebase.

### Reactivate account

1. Enable the Firebase user.
2. Record the audit event.
3. Require the user to sign in again.

Deactivation does not delete the user's usage or billing history.

## 7. Trial and subscription model

### Offer

- Three-day trial.
- $19.99 USD per month afterward.
- Automatic monthly renewal until canceled.
- Recommended: collect a payment method at trial enrollment.
- Recommended: cancellation remains effective through the current trial or paid period.

Suggested customer-facing language:

> 3 days free, then $19.99/month. Cancel before your trial ends to avoid being charged. Your subscription renews monthly until canceled.

Checkout must show the exact first-charge date and recurring amount.

### Trial start

Recommended: start the trial only after hosted checkout succeeds and a verified webhook establishes the subscription. Do not start it when a Firebase account is merely created.

### Trial reminders

- Show the precise trial end in the application.
- Send a reminder roughly 24 hours before the first charge.
- A short three-day trial must not depend solely on a provider event that may be emitted several days before trial end.

### Cancellation

- Users cancel through the payment provider's hosted customer portal.
- Set cancellation for the end of the current period unless product policy later changes.
- Continue access through `current_period_end` when payment is valid.

### Failed renewal

- Record `past_due` from verified webhook state.
- Display a clear billing warning and link to update the payment method.
- Recommended: allow a three-day grace period.
- Deny document processing after grace expires while keeping billing/account pages accessible.
- Restore access only after verified provider state confirms recovery.

### Complimentary access

Use the term **Complimentary access** rather than a permanent `is_free` boolean.

An override contains:

- Mode: `complimentary` or `internal`.
- Start time.
- Optional expiration time.
- Acting administrator UID.
- Safe internal reason.
- Created and updated timestamps.

An active override bypasses subscription requirements but never bypasses Firebase account deactivation.

## 8. Billing integration boundaries

Recommended provider: Stripe Checkout and Stripe Customer Portal.

### Server-created checkout

- The authenticated backend resolves the product and Price ID.
- The client never supplies an amount, currency, trial length, or trusted customer ID.
- Associate checkout with Firebase UID using server-controlled metadata or client reference data.
- Restrict each account to one current subscription.

### Webhooks

- Endpoint: `POST /api/webhooks/stripe` if Stripe is approved.
- Read the raw request body.
- Verify the provider signature before parsing or acting.
- Store each provider event ID with a unique constraint before applying state.
- Make all handlers idempotent and safe for retries and out-of-order delivery.
- The checkout success redirect is presentation only; it never grants access.

Minimum event coverage:

- Checkout completed or expired.
- Subscription created, updated, deleted, paused, or resumed.
- Trial nearing its end.
- Invoice paid.
- Invoice payment failed.

### Customer portal

Create short-lived portal sessions on demand for the authenticated user's server-owned customer ID. Use the portal for payment methods, invoices, cancellation, and supported reactivation.

## 9. Persistent data model

The exact migration syntax is deferred, but the logical model is approved for planning.

### `user_accounts`

- `firebase_uid` primary key
- `email_snapshot`
- `display_name_snapshot`
- `created_at`
- `last_seen_at`
- `updated_at`

Firebase remains authoritative for disabled status. A local disabled field, if added for reporting, is only a synchronized snapshot.

### `billing_customers`

- `firebase_uid` unique foreign key
- `provider`
- `provider_customer_id` unique
- `created_at`
- `updated_at`

### `subscriptions`

- `firebase_uid` unique foreign key for the initial one-plan model
- `provider_subscription_id` unique
- `provider_price_id`
- `status`
- `trial_started_at`
- `trial_ends_at`
- `current_period_ends_at`
- `cancel_at_period_end`
- `canceled_at`
- `grace_ends_at`
- `last_invoice_status`
- `last_provider_sync_at`
- `created_at`
- `updated_at`

### `access_overrides`

- `id`
- `firebase_uid`
- `mode`
- `starts_at`
- `expires_at` nullable
- `reason`
- `created_by_admin_uid`
- `revoked_by_admin_uid` nullable
- `revoked_at` nullable
- `created_at`

### `usage_events`

- `event_id`
- `firebase_uid`
- `request_id`
- `event_type`
- `outcome`
- `page_count`
- `input_bytes`
- `output_bytes`
- `ocr_page_count`
- `duration_ms`
- `safe_error_code`
- `occurred_at`

Use a unique idempotency key where a retried request could otherwise be counted twice.

### `usage_daily`

- `firebase_uid`
- `usage_date`
- Uploads accepted/rejected
- Scans completed/failed
- Redactions verified/failed
- Downloads issued
- Pages processed
- OCR pages processed
- Input/output bytes

### `admin_audit_log`

- `audit_id`
- `actor_admin_uid`
- `target_uid`
- `action`
- Safe before/after state
- `request_id`
- `occurred_at`

Audit rows are append-only. Do not place document identifiers, filenames, contents, findings, or payment credentials in audit data.

### `billing_webhook_events`

- `provider_event_id` primary key
- `event_type`
- `received_at`
- `processed_at`
- `processing_status`
- `safe_error_code`

Do not retain full webhook payloads indefinitely. Store only the minimum required for idempotency and support unless a defined retention policy approves more.

## 10. Usage definitions

Record only server-observed operational facts:

- Upload accepted or safely rejected.
- Input bytes and validated page count.
- Scan attempted, completed, or failed.
- OCR page count.
- Redaction attempted and verification outcome.
- Download issued by the server.
- Processing duration and safe failure category.

Do not claim a file was saved to the user's device. A server can record only that the download response was issued.

Never store filenames, PDF contents, page images, extracted text, findings, redacted values, manual rectangles, or custom terms.

## 11. API plan

### Current user

- `GET /api/me/access`
- `GET /api/me/usage`

### Billing

- `POST /api/billing/checkout`
- `GET /api/billing/status`
- `POST /api/billing/portal`
- `POST /api/webhooks/{provider}`

### Administration

- `GET /api/admin/summary`
- `GET /api/admin/users`
- `GET /api/admin/users/{uid}`
- `GET /api/admin/users/{uid}/usage`
- `PATCH /api/admin/users/{uid}/status`
- `POST /api/admin/users/{uid}/access-overrides`
- `DELETE /api/admin/users/{uid}/access-overrides/{override_id}`
- `GET /api/admin/audit`

Use cursor pagination for user, event, and audit lists. Administrative list responses must not include authentication or payment secrets.

## 12. User experience plan

### Account and billing screen

- Current access state.
- Trial time remaining and exact first-charge date.
- `$19.99/month` renewal disclosure.
- Current-period end or cancellation date.
- Usage for the current period.
- Start trial/subscribe action.
- Manage billing action.
- Payment-failure recovery action.

### Processing gate

When access is unavailable, keep login and billing available but disable upload and processing with a direct explanation and appropriate action.

### Administrator page `/admin`

Summary cards:

- Total Firebase users.
- Enabled and disabled accounts.
- Trialing, active, past-due, canceled, and complimentary users.
- Documents and pages processed this month.
- Conversion from trial to paid.
- Payment failures needing attention.

User table:

- User identity summary.
- Firebase account status.
- Billing/access status.
- Trial end or next renewal.
- Last activity.
- Documents and pages this month.
- Action menu.

User detail panel:

- Firebase creation and last-sign-in metadata.
- Subscription and trial summary.
- Usage over 7, 30, and 90 days.
- Complimentary-access controls.
- Account activation/deactivation.
- Safe administrative history.
- Link to the payment-provider customer record for authorized support staff.

Do not show document-specific history.

## 13. Abuse and cost controls

Before advertising unlimited processing, measure CPU, memory, OCR time, and average pages per customer.

Retain existing per-document limits and add configurable per-account limits:

- Trial documents and pages.
- Monthly documents and pages.
- Concurrent processing jobs.
- Daily burst limits.

Limits must be enforced atomically on the server. The admin page may show usage but cannot be the enforcement mechanism.

Trial eligibility should initially be one trial per Firebase UID and payment-provider customer. Stronger abuse controls can later consider verified email history and provider-side signals without storing card data.

## 14. Email events

Billing makes transactional email part of this phase. Plan templates for:

- Trial started.
- Trial ending soon with exact charge date and amount.
- Subscription activated.
- Payment failed.
- Subscription scheduled to cancel.
- Subscription ended.
- Account deactivated or reactivated by an administrator.

Do not include document names, findings, or sensitive processing details.

## 15. Delivery phases

### Phase 2A — persistence foundation

- Provision PostgreSQL for local/test/production environments.
- Add connection management and migrations.
- Create user, usage, override, subscription, webhook, and audit tables.
- Define backup, restoration, and retention procedures.

### Phase 2B — usage instrumentation

- Add one centralized usage recorder.
- Instrument upload, scan, OCR, redact, verification, and download boundaries.
- Add idempotency and aggregate jobs/queries.
- Confirm no document data enters persistent storage.

### Phase 2C — access policy

- Add `require_active_access` after Firebase identity verification.
- Add `GET /api/me/access`.
- Add trial/active/complimentary/past-due policy tests.
- Add document purge behavior on administrative deactivation.

### Phase 2D — administrator API and UI

- Add `require_admin`.
- Add secure first-admin bootstrap runbook.
- Implement summary, user, usage, status, override, and audit endpoints.
- Build `/admin` with desktop/mobile and accessibility verification.

### Phase 2E — billing sandbox

- Confirm the payment provider.
- Create the product and `$19.99/month` sandbox price.
- Implement hosted checkout, webhooks, status, and customer portal.
- Test a three-day trial using provider test clocks or equivalent facilities.
- Add failed-payment and cancellation recovery.

### Phase 2F — email and disclosure

- Select an email provider.
- Add billing lifecycle messages.
- Finalize pricing, renewal, cancellation, privacy, and terms disclosures.

### Phase 2G — production readiness

- Complete authorization, webhook replay, concurrency, and abuse tests.
- Configure production secrets outside source control.
- Configure database backups and perform a restore drill.
- Reconcile subscription state against the provider.
- Launch to a small allowlisted cohort before general availability.

## 16. Required test coverage

- Non-admin users receive 403 from every admin endpoint.
- Client-supplied role, UID, price, amount, and access values are ignored.
- Disabled and revoked users cannot process documents.
- Self-deactivation and final-admin deactivation are rejected.
- Complimentary access works only within its effective dates.
- Expired trial and canceled subscription block processing at the correct time.
- Past-due grace begins and ends correctly.
- Checkout redirect without a verified webhook grants nothing.
- Forged webhook signatures are rejected.
- Duplicate and out-of-order webhook events are safe.
- Payment recovery restores access only after verified provider state.
- Usage retries do not double-count.
- Download tracking says issued, never saved.
- No persistent table, log, audit row, or metric contains document content or sensitive findings.
- Cross-user and cross-admin authorization boundaries remain enforced.

## 17. Definition of done

Phase 2 is complete only when:

- Administrators can safely view aggregate usage and manage account status.
- Complimentary access is distinct from billing state and fully audited.
- Trial and subscription access are granted only from verified server-side state.
- Customers can start a trial, pay, cancel, update payment methods, and recover failed billing.
- Usage and access limits are enforced server-side.
- Database backup and restore are documented and tested.
- Privacy review confirms that no document contents or sensitive findings are persisted.
- Automated security, billing, webhook, usage, and authorization tests pass.
- Production rollout and rollback procedures are documented.

