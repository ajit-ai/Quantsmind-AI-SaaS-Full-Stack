# Quantsmind AI SaaS — Overview & Product Vision

> Version: 1.0.0 | Date: 2026-09-02 | Branch: develop → main | Author: Ajit Kumar

## 1. Purpose
Quantsmind is an AI-powered SaaS platform. The existing codebase was fragmented/poorly documented. This redesign rebuilds production-grade full-stack system from scratch while preserving salvageable assets: model artifacts, business rules, DB schema and user data.

## 2. Goals
- Modern responsive SaaS UX (marketing, auth, onboarding, dashboard, billing/usage, admin)
- Secure multi-tenant backend with RBAC, metering, and Stripe billing
- Isolated, scalable AI inference microservice
- Single CI/CD pipeline, staging + production, observable (Sentry + OTEL)

## 3. Non-Goals (v1)
- No DB-per-tenant (use row-level isolation)
- No on-prem deployment
- No custom payment gateway (Stripe only)

## 4. Personas & Roles
| Persona | Role | Access |
|---------|------|--------|
| End User | member | tenant-scoped data + AI features |
| Tenant Admin | admin | member + billing, member mgmt, settings |
| Tenant Owner | owner | admin + delete tenant, Stripe portal |
| Platform Admin | super_admin | cross-tenant read, impersonation, feature flags |
| System | service | webhook, metering, internal AI calls |

## 5. Key User Flows (must pass E2E)
1. Signup → Email verify → Create/Join tenant → Onboarding → Core AI action → View usage → Subscribe via Stripe Checkout → Customer Portal manage plan
2. AI inference: `POST /api/v1/ai/predict` → queue → inference service → result cached → metering event → usage dashboard
3. Admin: list tenants, revenue, impersonate, toggle feature flags

## 6. Success Metrics
- E2E pass rate 100% for critical flows (Playwright)
- AI p95 latency < 800ms (non-streaming), < 250ms cached
- 99.9% API availability, < 300ms p95 for CRUD
- Stripe webhook reconciliation 100%, metering drift < 0.1%
