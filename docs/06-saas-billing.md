# SaaS Layer — Multi-Tenancy, Billing, Metering, Admin

## 1. Multi-Tenancy
- Strategy: **row-level** (`tenant_id` column) — pragmatic default. Indexes on every tenant-scoped table.
- Enforcement: NestJS `TenantGuard` + Prisma extension + RLS future. Every query scoped; super_admin explicit bypass with audit.
- Tenant lifecycle: create → invite members → plan change → cancel (soft delete, retain audit).

## 2. Roles (RBAC)
| Role | Permissions |
|------|-------------|
| owner | all tenant ops, billing portal/checkout, delete tenant, invite/remove, change roles |
| admin | billing read, invite/remove member, ai predict, usage view |
| member | ai predict, view own usage, read tenant |
| super_admin | cross-tenant read, impersonate, flags, revenue overview |

Guard: `@Roles('owner','admin')` + `@Tenant()` decorator. Policy tested per endpoint.

## 3. Stripe Integration
### Products/Prices
- `free` (0), `pro` ($29/mo + metered ai_calls $0.02), `enterprise` (contract). Prices in Stripe Dashboard, IDs in env `STRIPE_PRICE_PRO`, `STRIPE_PRICE_METERED`.

### Flows
- **Checkout**: `POST /billing/checkout {priceId}` → Stripe `checkout.sessions.create` (mode subscription, customer = tenant's stripeCustomerId) → return `url` → redirect → webhook `checkout.session.completed` → create `Subscription`.
- **Portal**: `POST /billing/portal` → `billingPortal.sessions.create` → return `url` for self-serve plan/cancel.
- **Webhooks**: `POST /billing/webhook` verifies `stripe-signature`. Handle: `customer.subscription.created/updated/deleted`, `invoice.paid/failed`, `checkout.session.completed`. Idempotent via `stripeEventId` dedup table (or log). Sync to `Subscription` + `Tenant.plan`.

### Metered Usage
- Billable action: `ai_calls` (1 per predict) + optional `tokens`. Emit `UsageEvent` on every predict (idempotencyKey = hash(requestId)).
- Worker cron (every 15m or hourly): `SELECT tenantId, sum(quantity) WHERE createdAt > lastFlush GROUP BY tenantId` → `stripe.subscriptionItems.createUsageRecord` (quantity). Reconcile daily; alert drift >0.1%.

## 4. Usage Metering & Events
- Queue: BullMQ `usage.aggregate` job.
- Dashboard: `GET /billing/usage?range=30d` → aggregated daily counts for chart.
- Retention: `UsageEvent` kept 13 months (billing disputes).

## 5. Admin Dashboard
- **Tenant list**: table (name, slug, plan, MRR, createdAt, status) + search/filters, pagination.
- **Tenant detail**: subscription, usage chart, members, recent AiRequests, audit log.
- **Revenue**: MRR, churn, ARPU (derived from Stripe + local).
- **Impersonation**: `POST /admin/impersonate {tenantId}` → short-lived (5m) scoped JWT with `impersonatedBy` claim; all actions audited.
- **Feature flags**: `FeatureFlag` table, UI toggle per tenant / global; checked via `FlagsService.isEnabled(key, tenantId)`.

## 6. Compliance & Ops
- Webhook retries: Stripe retries 72h; our handler idempotent.
- Dunning: Stripe Smart Retries + `invoice.payment_failed` → email + in-app banner.
- Data export: `GET /admin/tenants/:id/export` (GDPR).
- Hardening TODO: Stripe test clocks for E2E billing tests.
