# Quantsmind AI SaaS — Full-Stack (v1)

> Production-grade AI SaaS rebuilt from scratch. Architecture + Phase 1 scaffold live on `main` (via `develop`). Stack: React 18 + NestJS + Prisma + FastAPI + PostgreSQL + Redis + Stripe.

## Quick Links
| Doc | Path |
|-----|------|
| Overview & Vision | [`docs/00-overview.md`](docs/00-overview.md) |
| Architecture + Integration Diagram | [`docs/01-architecture.md`](docs/01-architecture.md) |
| Stack Decision | [`docs/02-stack-decision.md`](docs/02-stack-decision.md) |
| DB Schema (Prisma, multi-tenant) | [`docs/03-database-schema.md`](docs/03-database-schema.md) |
| API Spec (OpenAPI) | [`docs/04-api-spec.md`](docs/04-api-spec.md) |
| AI Service (FastAPI) | [`docs/05-ai-service.md`](docs/05-ai-service.md) |
| SaaS Billing (Stripe + metering) | [`docs/06-saas-billing.md`](docs/06-saas-billing.md) |
| Infra & DevOps (CI/CD, monitoring) | [`docs/07-infra-cicd.md`](docs/07-infra-cicd.md) |
| Consolidated Build Prompt | [`docs/08-consolidated-prompt.md`](docs/08-consolidated-prompt.md) |
| How to Run (all OS) | [`docs/09-how-to-run.md`](docs/09-how-to-run.md) |

## Stack at a Glance
- **Frontend** `apps/web` — React 18 + TS + Vite, Tailwind, shadcn/ui, React Query, Zustand, Framer Motion
- **Backend** `apps/api` — NestJS (Node 20) + Prisma + PostgreSQL 16 + Redis 7 + BullMQ, JWT (15m/7d) + RBAC, Stripe
- **AI** `services/ai-service` — FastAPI (Python 3.11), `/predict /health /metrics /batch/predict`, Redis cache, independent GPU scaling
- **Infra** Docker + GitHub Actions → Fly.io/Render (simple) or AWS ECS/GCP, Sentry + OpenTelemetry

## Architecture — High-Level
```
Cloudflare/CDN
      │
      ▼
  [web] React Vite (5173→443, CDN static)
      │ HTTPS / REST (OpenAPI at /api/docs)
      ▼
  [api] NestJS (3000) ──► Stripe API / Webhooks
   │  │  JWT + TenantGuard (row-level tenant_id) + Throttler(Redis)
   │  ├──► PostgreSQL 16 (Prisma, row-level MT)
   │  ├──► Redis 7 + BullMQ (ai jobs, usage metering, webhooks)
   │  └──► [ai-service] FastAPI (8000) — /predict /health /metrics (X-Internal-Token)
   │              │ (optional GPU) → S3/R2 (model artifacts, logs)
   ▼
 Sentry + OTEL → Grafana/Datadog | GH Actions → GHCR → Fly/Render or AWS/GCP
```
Full diagrams: [`docs/01-architecture.md`](docs/01-architecture.md) (integration), [`docs/07-infra-cicd.md`](docs/07-infra-cicd.md) (DevOps pipeline).

## Component Integration Diagram
```
apps/web (React Query) ──POST /api/v1/ai/predict──► apps/api (validate→rateLimit→BullMQ→cacheCheck)
                                                          │ if miss ──HTTP X-Internal-Token──► services/ai-service /predict
                                                          │          ◄──{result,tokens,latency}──
                                                          ├──► persist AiRequest + UsageEvent (Prisma) ──► PostgreSQL
                                                          ├──► Redis cache (sha256(prompt+params+version) TTL 1h)
                                                          └──► worker flush hourly ──► Stripe metered usage
Stripe webhook ──POST /billing/webhook──► apps/api ──► Subscription + Tenant.plan sync
Admin dashboard ──GET /admin/* (super_admin)──► apps/api ──► cross-tenant read + impersonate (audited)
```
Contracts: `POST /predict` `docs/04-api-spec.md`, Prisma schema `docs/03-database-schema.md`, AI contract `docs/05-ai-service.md`.

## DevOps Pipeline
```
push → develop ──► GH Actions ci.yml: lint → test (postgres+redis) → build (docker buildx) → e2e (Playwright)
                    │                                                          │
                    └─► GHCR ghcr.io/ajit-ai/quantsmind-* :sha ─────────────► deploy staging (auto, Fly/Render)
push → main ──► same build ──► approval gate (environment: production) ──► deploy prod + prisma migrate deploy + Sentry release
PR → develop/main ──► lint/test/build (no deploy)
```
Images: `web`, `api`, `ai-service` — `linux/amd64,arm64` (`docker-compose.yml`). Monitoring: Sentry + OTEL → Grafana. See `docs/07-infra-cicd.md`.

## How to Run

### Prerequisites
Node 20 + pnpm 9, Python 3.11, Docker Desktop (Win/Mac/BSD via Docker), Git. Per-OS native (without Docker) see `docs/09-how-to-run.md`.

### 1. Clone & Env
```bash
git clone https://github.com/ajit-ai/Quantsmind-AI-SaaS-Full-Stack.git
cd Quantsmind-AI-SaaS-Full-Stack
cp .env.example .env        # fill JWT secrets, Stripe keys for billing
# Windows PowerShell: Copy-Item .env.example .env
```

### 2. Run with Docker (recommended — works on Windows/Linux/macOS/BSD)
```bash
docker compose up --build
# web  http://localhost:5173  (nginx, proxied /api)
# api  http://localhost:3000/api/v1  +  http://localhost:3000/api/docs (Swagger)
# ai   http://localhost:8000/health  +  /metrics  (internal token: dev-internal-token)
# pg   localhost:5432 (quantsmind/quantsmind), redis localhost:6379
docker compose down -v  # clean volumes
```

### 3. Run natively (without Docker)
```bash
# terminal 1 — postgres + redis (or use docker for just infra)
docker compose up postgres redis -d

# terminal 2 — api
cd apps/api && pnpm install && npx prisma generate && npx prisma migrate dev --name init
pnpm dev  # http://localhost:3000/api/v1/health

# terminal 3 — ai-service
cd services/ai-service && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000  # http://localhost:8000/health

# terminal 4 — web
cd apps/web && pnpm install && pnpm dev  # http://localhost:5173 (proxies /api to :3000)
```

### 4. Verify
```bash
curl http://localhost:3000/api/v1/health
curl -H "X-Internal-Token: dev-internal-token" http://localhost:8000/health
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -H "X-Internal-Token: dev-internal-token" -d '{"prompt":"hello"}'
```

Full per-OS (Windows PS, Linux, macOS, FreeBSD) + bundle matrix: `docs/09-how-to-run.md`.

## Repo Structure
```
apps/web                  # React + Vite + Tailwind + shadcn
apps/api                  # NestJS + Prisma (schema.prisma) + modules/auth,tenant,ai,billing,admin,health
services/ai-service       # FastAPI app/main.py, requirements.txt, Dockerfile
packages/shared-types     # shared DTOs (PredictRequest etc.)
packages/eslint-config    # shared eslint
docs/                     # 00..09 architecture, api, runbooks
docker-compose.yml        # postgres+redis+api+ai+web
.github/workflows/ci.yml  # lint→test→build→e2e→deploy staging/prod
.env.example              # all env vars validated at startup
```

## Bundles per Environment
| Env | Bundle | Notes |
|-----|--------|-------|
| Windows | `web-dist.zip`, `api-windows-x64.zip` (+ win32 argon2/prisma engine), `ai-service-windows.zip` | Build on `windows-latest` runner |
| Linux | `*.tar.gz` (debian) or **Docker** `ghcr.io/...:sha` | `linux/amd64+arm64` |
| macOS | `api-darwin-arm64/x64.tar.gz` | Apple Silicon + Intel |
| BSD | `api-bsd.tar.gz` via FreeBSD VM | Prisma native engine built on BSD |
| **Recommended prod** | **Docker images** (linux) — run on all via Docker | Single pipeline, no per-OS drift |

Details: `docs/07-infra-cicd.md` + `docs/09-how-to-run.md`.

## Branches & Releases
- `develop` → auto deploys **staging** (`https://staging.quantsmind.ai`)
- `main` → manual approval → **production** (`https://quantsmind.ai`) + `prisma migrate deploy`
- `feature/*` → PR to `develop` (lint/test/build required)

## Scripts
| Scope | Command |
|-------|---------|
| root | `pnpm dev` (parallel), `pnpm build`, `pnpm lint`, `pnpm test` |
| web | `pnpm --filter @quantsmind/web dev/build/test` |
| api | `pnpm --filter @quantsmind/api dev/build/test`, `npx prisma migrate dev`, `npx prisma generate` |
| ai | `pip install -r services/ai-service/requirements.txt && uvicorn app.main:app --reload` |

## Contributing
Read `docs/00-overview.md` + `docs/02-stack-decision.md` before large changes. Confirm backend language (NestJS vs FastAPI) and auth provider (`jwt` vs Clerk/Auth0 via `AUTH_PROVIDER`) before scaffold. Lint/test must pass; E2E `signup→predict→billing` required.

## License
Private — Ajit Kumar. See repo.
