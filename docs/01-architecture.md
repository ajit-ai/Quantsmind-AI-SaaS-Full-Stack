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
                               │ HTTPS / REST (OpenAPI)
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
CI/CD: GitHub Actions → Docker → Render/Fly.io (simple) or AWS ECS/GCP Cloud Run (scale)
```

## 2. Service Boundaries
| Service | Repo Path | Port | Scaling |
|---------|-----------|------|---------|
| web | `apps/web` | 5173→443 | CDN + static |
| api | `apps/api` | 3000 | horizontal (stateless) |
| ai-service | `services/ai-service` | 8000 | independent, GPU optional |
| worker | `apps/api` (BullMQ worker) | — | scale with queue depth |
| postgres | docker / managed | 5432 | single primary + read replica later |
| redis | docker / managed | 6379 | single, persistence AOF |

## 3. Request Flows
### 3.1 Auth
`POST /auth/register` → hash (argon2) → create user+tenant+member(OWNER) → issue access(15m)+refresh(7d, httpOnly) → `POST /auth/refresh`
Managed alternative: Clerk/Auth0 OIDC drop-in (feature flag `AUTH_PROVIDER`).

### 3.2 Tenant Isolation
Middleware `TenantGuard` resolves `tenantId` from JWT + `x-tenant-id`, enforces `WHERE tenant_id = :tid` on every Prisma query via extension. Super_admin bypass with audit log.

### 3.3 AI Predict
```
web → POST /api/v1/ai/predict {prompt, params}
api → validate (Zod) → rate limit (Redis) → enqueue BullMQ `ai.job`
    → if cache hit (Redis, sha256(prompt+modelVersion)) return cached
    → else HTTP → ai-service /predict → ai-service returns {result, tokens, latency}
api → persist AiRequest + UsageEvent → return result
worker (async) → aggregate usage → Stripe metered usage (hourly flush)
```

## 4. Frontend Architecture
```
apps/web/src/
├── app/ (routes, layouts, error boundaries)
├── features/ (auth, billing, dashboard, ai, admin) — vertical slices
├── components/ui/ (shadcn primitives)
├── hooks/, lib/ (api client, query keys), stores/ (zustand)
└── tests/ (vitest + Playwright)
```
- **Server state**: TanStack Query (caching, dedup, optimistic)
- **Client state**: Zustand (theme, sidebar, onboarding)
- **Forms**: react-hook-form + zodResolver
- **Motion**: framer-motion subtle
- **Dark mode**: `next-themes` pattern via Tailwind `dark:`

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
│   └── health/
├── common/ (filters, interceptors, pipes, decorators)
├── prisma/ (schema, migrations)
└── queue/ (bullmq processors)
```
- **Validation**: `class-validator` + `class-transformer` (or Zod via `zodValidationPipe`)
- **Rate limiting**: `@nestjs/throttler` backed by Redis, per-tenant + per-IP
- **OpenAPI**: `@nestjs/swagger`, spec served at `/api/docs`, generated to `docs/openapi.json`
- **Testing**: Jest unit + Supertest integration + Playwright E2E (separate `e2e/`)

## 6. Cross-Cutting Concerns
- **Config**: `@nestjs/config` + `.env.example` validated via Joi/Zod
- **Logging**: pino, correlationId via `cls-hooked`
- **Errors**: Global `HttpExceptionFilter` → RFC7807 problem+json
- **Security**: Helmet, CORS allowlist, CSRF for cookies, argon2, row-level tenant isolation, audit log
- **Migrations**: Prisma `migrate deploy` in CI

## 7. Deployment Topology
- **Simple**: Fly.io / Render — 1 Dockerfile per service, `docker-compose.yml` for local.
- **Scale**: AWS ECS Fargate + RDS Postgres + ElastiCache Redis + S3 + CloudFront.
- Both share same GitHub Actions pipeline (build → test → push image → deploy staging → manual approve → prod).

## 8. ADR Summary
| # | Decision | Rationale |
|---|----------|-----------|
| AD-01 | NestJS over Express bare | DI, guards, interceptors, testability out-of-box |
| AD-02 | Row-level multi-tenancy | Lowest ops, 95% SaaS needs; migrate to schema-per-tenant only if compliance demands |
| AD-03 | Separate AI service (FastAPI) | Isolate ML deps, independent GPU scaling, stable contract |
| AD-04 | Prisma + PostgreSQL | Type-safe, migrate tooling, relational integrity for billing |
| AD-05 | Stripe only | De-facto, handles subs + metered + portal + dunning |

## 9. Repo Structure (target)
```
/
├── apps/
│   ├── web/              # React + Vite
│   └── api/              # NestJS
├── services/
│   └── ai-service/       # FastAPI
├── packages/
│   ├── shared-types/     # DTOs, OpenAPI types
│   └── eslint-config/
├── docs/                 # architecture, api, runbooks
├── docker-compose.yml
├── .github/workflows/ci.yml
└── .env.example
```
