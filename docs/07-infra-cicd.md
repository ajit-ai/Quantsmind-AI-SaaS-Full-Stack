# Infra, CI/CD, Monitoring & Security

## 1. Environments
| Env | Branch | URL | Deploy |
|-----|--------|-----|--------|
| local | any | http://localhost:5173 (web), :3000 (api), :8000 (ai) | docker-compose up |
| staging | develop | https://staging.quantsmind.ai | auto on push to develop |
| production | main | https://quantsmind.ai | manual approve after staging |

## 2. Docker
- `apps/web/Dockerfile` — multi-stage: build (node) → nginx:alpine serve static + proxy /api.
- `apps/api/Dockerfile` — node:20-alpine, `prisma generate`, `npm run build`, `node dist/main`.
- `services/ai-service/Dockerfile` — python:3.11-slim, pip install, uvicorn.
- `docker-compose.yml` — postgres:16-alpine, redis:7-alpine, api, ai-service, web; volumes `pgdata`, `redisdata`.

## 3. CI/CD — `.github/workflows/ci.yml`
```yaml
on:
  push: { branches: [develop, main] }
  pull_request: { branches: [develop, main] }
jobs:
  lint:   { runs: pnpm lint, ruff check }
  test:   { runs: pnpm test, pytest, prisma migrate diff check }
  build:  { runs: docker build --cache-from ghcr.io/... }
  e2e:    { runs: playwright (against compose) — signup → predict → billing mock }
  deploy-staging: { if: branch==develop, needs: [lint,test,build,e2e], uses: flyctl/render deploy }
  deploy-prod:    { if: branch==main, needs: deploy-staging, environment: production (approval) }
```
- Images pushed to GHCR `ghcr.io/ajit-ai/quantsmind-*:<sha>`.
- Migrations: `prisma migrate deploy` as init container / release command.
- OpenAPI export: `pnpm openapi:export` → diff check, artifact `openapi.json`.

## 4. Cloud Targets
- **Simple (default)**: Fly.io or Render — low ops, Dockerfile-native, auto TLS.
- **Scale**: AWS ECS Fargate + RDS + ElastiCache + S3 + CloudFront OR GCP Cloud Run + Cloud SQL + Memorystore.
- IaC: `infra/` with Terraform (optional) — same compose for both.

## 5. Monitoring
- **Errors**: Sentry — `@sentry/react` (web) + `@sentry/nestjs` (api) + `sentry-sdk` (ai-service). Release + `tracesSampleRate 0.1`.
- **Metrics/Traces**: OpenTelemetry SDK → OTLP → Grafana Cloud / Datadog. RED metrics per endpoint, queue depth, ai latency histogram.
- **Uptime**: Better Stack / UptimeRobot ping `/health`.
- **Logs**: pino JSON (api), uvicorn JSON (ai), shipped to Loki/CloudWatch; correlation via `x-request-id`.

## 6. Security Checklist
- [ ] Helmet, CORS allowlist (staging/prod domains only)
- [ ] JWT short-lived access (15m) + rotating refresh (httpOnly, Secure, SameSite Lax)
- [ ] argon2 password hashing, rate limit login 5/min
- [ ] Tenant isolation tests (cross-tenant 403)
- [ ] Stripe webhook signature verification
- [ ] `X-Internal-Token` for ai-service, secrets via env / Doppler / Vault — no hardcode
- [ ] Dependency audit (`pnpm audit`, `pip-audit`) in CI, Dependabot
- [ ] Backup: daily pg_dump to S3, PITR enabled on managed Postgres

## 7. Performance Targets
- API CRUD p95 < 300ms, AI p95 < 800ms (cached < 250ms)
- Web Lighthouse > 90, TTFB < 200ms via CDN
- Load test: k6 `POST /ai/predict` 50 rps sustained

## 8. Runbooks
- `docs/runbooks/deploy.md` — rollback via previous image tag
- `docs/runbooks/stripe.md` — replay webhook: `stripe events resend`
- `docs/runbooks/ai.md` — model rollback via `modelVersion` switch
