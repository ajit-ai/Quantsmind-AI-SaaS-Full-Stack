# Infra, CI/CD, DevOps & Monitoring

## 1. Environments
| Env | Branch | URL | Deploy | DB |
|-----|--------|-----|--------|----|
| local | any | http://localhost:5173 (web), :3000 (api), :8000 (ai) | `docker compose up` | postgres:16 + redis:7 (compose) |
| staging | `develop` | https://staging.quantsmind.ai | auto on push to `develop` | managed Postgres + Redis |
| production | `main` | https://quantsmind.ai | manual approve after staging | managed + PITR + daily S3 dump |

## 2. Docker
- `apps/web/Dockerfile` — multi-stage: build (node) → nginx:alpine serve static + proxy `/api` (see `nginx.conf`).
- `apps/api/Dockerfile` — node:20-alpine, `pnpm install`, `prisma generate` (per-arch engine), `npm run build`, `node dist/main`.
- `services/ai-service/Dockerfile` — python:3.11-slim, `pip install -r requirements.txt`, `uvicorn app.main:app`.
- `docker-compose.yml` — postgres:16-alpine, redis:7-alpine (AOF), api (3000), ai-service (8000), web (80→5173); volumes `pgdata`, `redisdata`; healthchecks.

## 3. DevOps Pipeline Diagram
```
                     ┌─────────────────────────────────────────────────┐
                     │  GitHub — push to develop / main / PR           │
                     └──────────────────┬──────────────────────────────┘
                                        │
                     ┌──────────────────▼──────────────────────────────┐
                     │  .github/workflows/ci.yml                        │
                     │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐         │
                     │  │ lint │→ │ test │→ │ build│→ │  e2e │         │
                     │  │ pnpm │  │ jest │  │docker│  │ PW   │         │
                     │  │ ruff │  │pytest│  │buildx│  │signup│         │
                     │  │      │  │ pg+  │  │cache │  │→pred→│         │
                     │  │      │  │ redis│  │ GHCR │  │ bill │         │
                     │  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘         │
                     └─────┼─────────┼─────────┼─────────┼─────────────┘
                           │         │         │         │
              PR (no deploy)│         │         │         │
                           └─────────┴─────────┴─────────┘
                                        │
                     ┌──────────────────▼──────────────────────────────┐
                     │  GHCR: ghcr.io/ajit-ai/quantsmind-{web,api,ai}  │
                     │  tags: :sha, :develop, :latest (multi-arch)     │
                     └──────────────────┬──────────────────────────────┘
                                        │
               ┌────────────────────────┼────────────────────────┐
               │                        │                        │
     develop branch            PR checks only           main branch
               │                        │                        │
     ┌─────────▼─────────┐           (stop)        ┌────────────▼──────────┐
     │ deploy staging    │                         │ deploy production     │
     │ Fly/Render auto   │                         │ approval gate         │
     │ + prisma migrate  │                         │ environment: prod     │
     │ deploy            │                         │ + prisma migrate      │
     │ + Sentry release  │                         │ deploy + healthcheck  │
     └─────────┬─────────┘                         └────────────┬──────────┘
               │                                                │
     ┌─────────▼─────────┐                         ┌────────────▼──────────┐
     │ Smoke: /health    │                         │ Smoke + rollback      │
     │ /api/docs, E2E    │                         │ previous image tag    │
     └───────────────────┘                         └───────────────────────┘
```

**Jobs (ci.yml):**
```yaml
on: { push: {branches: [develop, main]}, pull_request: {branches: [develop, main]} }
jobs:
  lint:   { runs: pnpm lint, ruff check services/ai-service }
  test:   { services: {postgres:16, redis:7}, runs: pnpm test, pytest, prisma migrate diff }
  build:  { runs: docker/setup-buildx, docker compose config, docker build --cache-from ghcr.io/... → push ghcr.io/...:sha (linux/amd64,arm64) }
  e2e:    { if: develop||PR, runs: playwright against compose — signup → predict → billing mock }
  deploy-staging: { if: develop, needs: [lint,test,build,e2e], environment: staging, flyctl/render deploy }
  deploy-prod:    { if: main, needs: deploy-staging, environment: production (approval), migrate deploy }
```
- OpenAPI export: `pnpm openapi:export` → diff check → artifact `docs/openapi.json`.

## 4. Per-OS Bundles (final artifacts)
| OS | web | api | ai-service | How built |
|----|-----|-----|------------|-----------|
| **Windows** | `web-dist.zip` (dist + nginx.conf) | `api-windows-x64.zip` (dist + win32 argon2/prisma engine) | `ai-windows.zip` (venv) | `windows-latest` runner, `pnpm build`, `prisma generate` (win32) |
| **Linux** | `web-linux.tar.gz` | `api-linux-x64.tar.gz` (debian engine) | `ai-linux.tar.gz` | `ubuntu-latest` / Docker (recommended) |
| **macOS** | `web-darwin.tar.gz` (same) | `api-darwin-arm64/x64.tar.gz` | `ai-darwin.tar.gz` | `macos-latest` (arm64 + x64) |
| **BSD** | `web-bsd.tar.gz` | `api-bsd.tar.gz` | `ai-bsd.tar.gz` | `vmactions/freebsd-vm` + native `prisma generate` |
| **Universal prod** | **Docker** `ghcr.io/.../web:sha` | **Docker** `ghcr.io/.../api:sha` | **Docker** `ghcr.io/.../ai:sha` | `docker/buildx` linux/amd64,arm64 — runs on **all** via Docker Desktop |

Recommended prod: **Docker images** — single build, no per-OS drift. Bare-metal: unzip per-OS bundle + set `.env.example` vars + `Node 20`/`Python 3.11`.

## 5. Cloud Targets
- **Simple (default)**: Fly.io or Render — Dockerfile-native, auto TLS, `flyctl deploy` / `render deploy`.
- **Scale**: AWS ECS Fargate + RDS Postgres + ElastiCache Redis + S3 + CloudFront OR GCP Cloud Run + Cloud SQL + Memorystore.
- IaC: `infra/` Terraform (optional) — same compose for both. Secrets via env / Doppler / Vault.

## 6. Monitoring
- **Errors**: Sentry — `@sentry/react` (web) + `@sentry/nestjs` (api) + `sentry-sdk` (ai) — `tracesSampleRate 0.1`, release = git sha.
- **Metrics/Traces**: OpenTelemetry SDK → OTLP → Grafana Cloud / Datadog. RED per endpoint, queue depth, ai latency histogram.
- **Uptime**: Better Stack / UptimeRobot ping `/health` every 30s.
- **Logs**: pino JSON (api) + uvicorn JSON (ai) → Loki/CloudWatch; correlation via `X-Request-Id` propagated web→api→ai.

## 7. Security Checklist
- [ ] Helmet, CORS allowlist (staging/prod domains only)
- [ ] JWT access 15m + rotating refresh httpOnly Secure SameSite=Lax
- [ ] argon2, rate limit login 5/min, Throttler per-tenant
- [ ] Tenant isolation tests (cross-tenant 403)
- [ ] Stripe webhook signature verification
- [ ] `X-Internal-Token` for ai-service
- [ ] `pnpm audit`, `pip-audit` in CI + Dependabot
- [ ] Backup: daily `pg_dump` to S3, PITR on managed Postgres

## 8. Performance Targets
- API CRUD p95 <300ms, AI p95 <800ms (cached <250ms)
- Web Lighthouse >90, TTFB <200ms via CDN
- Load: k6 `POST /ai/predict` 50 rps sustained

## 9. Runbooks
- `docs/runbooks/deploy.md` — rollback: `fly releases rollback` / redeploy previous GHCR tag
- `docs/runbooks/stripe.md` — replay webhook: `stripe events resend` + idempotencyKey dedup
- `docs/runbooks/ai.md` — model rollback via `modelVersion` switch / canary routing
- How to run all envs: `docs/09-how-to-run.md`
