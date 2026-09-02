# Architecture — Quantsmind AI SaaS Full-Stack (v1)

## 1. High-Level Diagram
```
                     ┌─────────────────────┐
                     │   Cloudflare / CDN  │
                     └─────────┬───────────┘
                               │
               ┌───────────────▼────────────────┐
               │  Frontend: React 18 + Vite     │
               │  TS, Tailwind, shadcn/ui       │
               │  React Query + Zustand         │
               └───────────────┬────────────────┘
                               │ HTTPS / REST (OpenAPI at /api/docs)
               ┌───────────────▼────────────────┐
               │  API Gateway / Backend         │◄──── Stripe Webhooks
               │  NestJS (Node 20) + Prisma     │────► Stripe API
               │  JWT (access+refresh), RBAC,   │
               │  Zod/class-validator, Throttler│
               └─┬──────────────┬───────────────┘
                 │              │
     ┌───────────▼──────┐ ┌─────▼─────────────┐ ┌──────────────────┐
     │ PostgreSQL 16    │ │ Redis 7 + BullMQ  │ │ AI Inference SVC │
     │ (row-level MT)   │ │ queue: metering,  │ │ FastAPI + Python │
     │ Prisma Migrate   │ │ async AI jobs,    │ │ /predict /health │
     └──────────────────┘ │ webhooks          │ │ /metrics, cache  │
                         └───────────────────┘ └────────┬─────────┘
                                                        │ (optional GPU)
                                                        ▼
                                               ┌──────────────────┐
                                               │ Object Storage   │
                                               │ (S3/R2) model    │
                                               │ artifacts/logs   │
                                               └──────────────────┘

Observability: Sentry (FE+BE) + OpenTelemetry → Grafana/Datadog
CI/CD: GitHub Actions → GHCR → Render/Fly.io (simple) or AWS ECS/GCP Cloud Run (scale)
```

## 2. Service Boundaries
| Service | Repo Path | Port | Scaling | Bundle |
|---------|-----------|------|---------|--------|
| web | `apps/web` | 5173→443 | CDN + static | `dist/` static (OS-agnostic) + Docker nginx:alpine |
| api | `apps/api` | 3000 | horizontal (stateless) | `dist/main.js` + native `argon2`/`prisma` per OS + Docker node:20-alpine |
| ai-service | `services/ai-service` | 8000 | independent, GPU optional | Python venv + Docker python:3.11-slim |
| worker | `apps/api` (BullMQ) | — | scale with queue depth | same as api |
| postgres | docker / managed | 5432 | primary + replica later | — |
| redis | docker / managed | 6379 | AOF persistence | — |

## 3. Integration Component Diagram (detailed)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Client (apps/web)                                                          │
│  React Router + React Query (server state) + Zustand (UI) + RHF+Zod         │
│  apiClient (fetch, x-tenant-id, Idempotency-Key, attach JWT)                │
└──────────────┬──────────────────────────────────────────────────────────────┘
               │ 1. POST /api/v1/auth/*, /ai/predict, /billing/*, /admin/*
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  api (apps/api/src) — NestJS                                                │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Auth    │  │  Tenant  │  │    AI      │  │ Billing  │  │  Admin   │    │
│  │ register │  │ TenantGuard│ │ validate │  │ checkout │  │ tenants  │    │
│  │ login    │◄─┤ RBAC     │◄─┤ rateLimit│◄─┤ portal   │◄─┤ imperson │    │
│  │ refresh  │  │ membership│  │ BullMQ   │  │ webhook  │  │ flags    │    │
│  └────┬─────┘  └────┬─────┘  └─────┬──────┘  └────┬─────┘  └────┬─────┘    │
│       │             │              │               │             │          │
│  ┌────▼─────────────▼──────────────▼───────────────▼─────────────▼───────┐ │
│  │  Common: Helmet/CORS, ValidationPipe, HttpExceptionFilter (RFC7807),   │ │
│  │  pino + correlationId, @nestjs/throttler(redis), @nestjs/swagger       │ │
│  └──────────────────────────┬──────────────────────────────────────────────┘ │
└─────────────────────────────┼──────────────────────────────────────────────┘
                              │ 2a. Prisma (tenantExtension → WHERE tenant_id)
                              ▼
                    ┌──────────────────┐
                    │   PostgreSQL 16  │  Tenant, User, Membership, AiRequest,
                    │  Prisma Migrate  │  UsageEvent, Subscription, AuditLog
                    └──────────────────┘
                              │ 2b. enqueue / cache
                              ▼
                    ┌──────────────────┐         3. HTTP X-Internal-Token
                    │  Redis + BullMQ  │ ───────────────────────►┌──────────────────┐
                    │  ai.job, usage   │◄────────────────────────│  ai-service      │
                    │  cache: sha256() │         {result,tokens} │  FastAPI /predict│
                    └──────────────────┘                          │  /batch /health  │
                              │                                   │  /metrics + cache│
                              │ 4. UsageEvent                     └────────┬─────────┘
                              ▼                                            │ (GPU opt)
                    ┌──────────────────┐                                     ▼
                    │ Stripe           │                            ┌──────────────────┐
                    │ subscriptions,   │                            │  S3/R2 (models)  │
                    │ metered usage,   │                            └──────────────────┘
                    │ portal, webhooks │ ──webhook──► api /billing/webhook (verify sig)
                    └──────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Observability      │
                    │ Sentry + OTEL → Grafana/Datadog, pino logs, /health/ready/live │
                    └────────────────────┘
```

### 3.1 Auth Flow
`POST /auth/register` → argon2 hash → create `User`+`Tenant`+`Membership(OWNER)` → issue access(15m)+refresh(7d httpOnly) → `POST /auth/refresh` rotates. Toggle `AUTH_PROVIDER=clerk|auth0` for managed OIDC.

### 3.2 Tenant Isolation
`TenantGuard` extracts `tenantId` from JWT + `x-tenant-id` header (mismatch 403). Prisma extension injects `WHERE tenant_id = :tid` for all tenant-scoped models. `super_admin` bypass audited via `AuditLog`.

### 3.3 AI Predict (integration sequence)
```
web: POST /api/v1/ai/predict {prompt, params} + Idempotency-Key
api: 1) Zod validate (max 8k chars) 2) Throttler (Redis 60/min IP, 120/min tenant)
     3) Check Redis cache sha256(prompt+params+version) → if hit return cached (p95 <250ms)
     4) else BullMQ enqueue ai.job → HTTP POST ai-service /predict (X-Internal-Token)
ai-service: load model (lifespan), run predict(), return {result,tokensIn,tokensOut}
api: persist AiRequest + UsageEvent(idempotencyKey) → return 200 {requestId,result,cached,latencyMs}
worker (async, BullMQ): aggregate UsageEvent per tenant/hour → stripe.subscriptionItems.createUsageRecord
reconcile: daily compare UsageEvent sum vs Stripe → alert drift >0.1%
```

### 3.4 Billing & Admin Integration
Stripe Checkout (`POST /billing/checkout` → 303 url) → `checkout.session.completed` webhook → create `Subscription`. Portal (`POST /billing/portal` → url). Admin `GET /admin/tenants` + `POST /admin/impersonate` (5m scoped JWT, audited).

## 4. Frontend Architecture
```
apps/web/src/
├── app/ (routes, layouts, error boundaries, providers: QueryClient, Theme)
├── features/ (auth, billing, dashboard, ai, admin) — vertical slices, each: components, hooks, api
├── components/ui/ (shadcn primitives — button, dialog, card, table)
├── hooks/, lib/ (apiClient, queryKeys, cn), stores/ (zustand: theme, sidebar)
└── tests/ (vitest unit + Playwright e2e)
```
- Server state: TanStack Query (cache, dedup, optimistic)
- Client state: Zustand
- Forms: react-hook-form + zodResolver
- Motion: framer-motion subtle; Dark mode: Tailwind `dark:` + class toggle

## 5. Backend Architecture (NestJS)
```
apps/api/src/
├── modules/
│   ├── auth/ (jwt, refresh, guards, strategies)
│   ├── tenant/ (tenant, membership, rbac)
│   ├── user/
│   ├── ai/ (controller → queue → ai-service client)
│   ├── billing/ (stripe service, webhooks, portal)
│   ├── usage/ (metering, aggregation)
│   ├── admin/ (tenant list, impersonation)
│   └── health/ (health, ready, live)
├── common/ (filters, interceptors, pipes, decorators, tenantExtension)
├── prisma/ (schema.prisma, migrations, seed)
└── queue/ (bullmq processors)
```
- Validation: class-validator + class-transformer (or zodValidationPipe)
- Rate limiting: @nestjs/throttler (Redis)
- OpenAPI: @nestjs/swagger at /api/docs → export docs/openapi.json
- Testing: Jest + Supertest + Playwright (e2e/ signup→predict→billing)

## 6. Cross-Cutting Concerns
- Config: @nestjs/config + .env.example validated via Joi/Zod
- Logging: pino JSON, correlationId (cls-hooked, X-Request-Id propagated to ai-service)
- Errors: Global HttpExceptionFilter → RFC7807 problem+json
- Security: Helmet, CORS allowlist, httpOnly refresh, argon2, row-level isolation, audit log
- Migrations: `prisma migrate deploy` in CI release step

## 7. Deployment Topology
- **Simple**: Fly.io / Render — 1 Dockerfile per service, docker-compose.yml local.
- **Scale**: AWS ECS Fargate + RDS + ElastiCache + S3 + CloudFront OR GCP Cloud Run + Cloud SQL + Memorystore.
- Both share same GH Actions pipeline (build → test → push GHCR → deploy staging auto → prod manual approve).

## 8. ADR Summary
| # | Decision | Rationale |
|---|----------|-----------|
| AD-01 | NestJS over Express bare | DI, guards, interceptors, testability |
| AD-02 | Row-level multi-tenancy | Lowest ops; 95% SaaS; migrate to schema-per-tenant only if compliance |
| AD-03 | Separate AI service (FastAPI) | Isolate ML deps, independent GPU scaling, stable contract |
| AD-04 | Prisma + PostgreSQL | Type-safe, migrations, relational integrity for billing |
| AD-05 | Stripe only | Subs + metered + portal + dunning natively |

## 9. Repo Structure
```
/ (root: package.json, pnpm-workspace.yaml)
├── apps/
│   ├── web/              # React + Vite
│   └── api/              # NestJS + Prisma
├── services/
│   └── ai-service/       # FastAPI
├── packages/
│   ├── shared-types/     # DTOs, OpenAPI types
│   └── eslint-config/
├── docs/                 # 00..09 architecture, api, runbooks
├── docker-compose.yml
├── .github/workflows/ci.yml
└── .env.example
```

## 10. Sequence: End-to-End (signup → predict → bill)
```
User → web: signup form → POST /auth/register → api creates tenant → 201 + tokens → web stores
User → web: prompt → POST /ai/predict → api (cached? → instant) → ai-service → UsageEvent → web renders result
Cron → worker: flush UsageEvent → Stripe metered → billing dashboard GET /billing/usage → chart
Owner → web: Manage billing → POST /billing/portal → Stripe portal → webhook → Subscription updated
```
