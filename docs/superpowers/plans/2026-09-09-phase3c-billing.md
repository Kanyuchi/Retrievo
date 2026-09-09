# Phase 3c: Billing (Stripe) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Checkbox steps.

**Goal:** Users can subscribe (Pro €19/mo, Team €25/seat/mo min 3, ACADEMIC50 coupon), payment flips their `plan_tier`, and they self-manage via Stripe's customer portal. Test mode end-to-end now; live is an env swap later.

**Stripe state (already created, test mode):** `STRIPE_SECRET_KEY`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_TEAM`, coupon `ACADEMIC50` — all in `.env`. Webhook endpoint + `STRIPE_WEBHOOK_SECRET` will be created via API at deploy (operator step).

## Tier mapping
Pro subscription → `plan_tier='pro'`; Team → `plan_tier='enterprise'` (existing QUOTA_LIMITS tiers; a dedicated 'team' tier is a later refinement). Cancellation/expiry → `'free'`.

## Backend (literature_rag/routers/billing.py — new; `stripe` pip package added to requirements)
- `User` migration: `stripe_customer_id` (String, nullable), `stripe_subscription_id` (String, nullable) — ALTER TABLE pattern in `_run_migrations`.
- `POST /api/billing/checkout` (auth): body `{plan: "pro"|"team", seats?: int (team, min 3, default 3), academic?: bool}` → get/create Stripe customer (store id), create Checkout Session: `mode=subscription`, `line_items=[{price, quantity: seats or 1}]`, `discounts=[{coupon: ACADEMIC50}]` when academic, `success_url=https://humbowo.com/settings/billing?status=success`, `cancel_url=...?status=cancelled`, `metadata={user_id, plan}` AND `subscription_data[metadata][user_id/plan]` → `{url}`.
- `POST /api/billing/portal` (auth): billing-portal session for the stored customer → `{url}`; 400 if no customer yet.
- `GET /api/billing/status` (auth): `{plan_tier, has_customer, subscription_id}`.
- `POST /api/billing/webhook` (NO auth dependency; verify `Stripe-Signature` with `stripe.Webhook.construct_event` + `STRIPE_WEBHOOK_SECRET`; 400 on bad signature): handle `checkout.session.completed` (read metadata.user_id/plan → set plan_tier + subscription id), `customer.subscription.updated` (status active→tier by plan metadata; past_due/unpaid → leave tier, log), `customer.subscription.deleted` (→ `free`, clear subscription id). Idempotent by design (setting state, not incrementing). Must be exempt from CSRF/auth middleware (verify the csrf middleware skips cookie-less requests; if not, whitelist the path).
- Register router in api.py.
- Tests (`tests/test_billing.py`): patch the `stripe` module (checkout/customer/portal creation return stubs) — checkout requires auth, returns url, persists customer id; team seats<3 → 400; webhook with patched `construct_event`: completed event flips plan_tier to pro/enterprise; subscription.deleted flips back to free; bad signature → 400.

## Frontend (webapp)
- New page `src/pages/settings/BillingPage.tsx` at `/settings/billing` + SettingsSidebar entry "Billing": shows current plan (from `GET /api/billing/status` + auth user), three plan cards (Free — current-state only; Pro €19/mo; Team €25/seat with seat stepper min 3), academic/NGO checkbox (adds 50% note), Upgrade buttons → `POST /api/billing/checkout` → `window.location = url`; "Manage subscription" button (visible when has_customer) → portal url redirect. Handle `?status=success|cancelled` query on return with a toast + status refetch.
- api.ts: `createCheckout(plan, seats?, academic?)`, `createPortalSession()`, `getBillingStatus()` — via the central fetch (auth+retry).
- Quota upsell: the KB-limit/doc-limit 403 error toasts link "Upgrade plan" → `/settings/billing` (grep for where quota 403 messages surface — KB create + upload paths).
- i18n EN/DE. Lint+build green.

## Operator/verify (me)
1. Create webhook endpoint via Stripe API (`url=https://humbowo.com/api/billing/webhook`, events: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted) → whsec into `.env`, ship, deploy.
2. Suite green (96+); deploy backend+frontend.
3. E2E on prod (test mode): register test user → checkout session URL opens (Playwright: Stripe checkout page renders) → complete with 4242 card via Playwright if feasible; fallback: create subscription directly via Stripe API for the test customer → webhook fires → verify plan_tier flipped in DB → portal URL opens → cancel via API → tier back to free. Cleanup test user.
4. Living docs; write `scripts/stripe_live_setup.py` note (recreate products in live mode) as a stub comment in plan — actual script when going live.
