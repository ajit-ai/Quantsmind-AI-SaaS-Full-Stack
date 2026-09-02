# Quantsmind AI SaaS — Full-Stack

> Production-grade AI SaaS rebuilt from scratch. Architecture v1 on `main` (via `develop`).

## Quick Links
- Architecture: [`docs/01-architecture.md`](docs/01-architecture.md)
- Stack Decision: [`docs/02-stack-decision.md`](docs/02-stack-decision.md)
- DB Schema (Prisma): [`docs/03-database-schema.md`](docs/03-database-schema.md)
- API Spec (OpenAPI): [`docs/04-api-spec.md`](docs/04-api-spec.md)
- AI Service: [`docs/05-ai-service.md`](docs/05-ai-service.md)
- SaaS Billing: [`docs/06-saas-billing.md`](docs/06-saas-billing.md)
- Infra & CI/CD: [`docs/07-infra-cicd.md`](docs/07-infra-cicd.md)
- Consolidated Prompt: [`docs/08-consolidated-prompt.md`](docs/08-consolidated-prompt.md)

## Stack
**Frontend** React 18 + TS + Vite, Tailwind, shadcn/ui, React Query, Zustand  
**Backend** NestJS (Node 20) + Prisma + PostgreSQL 16 + Redis 7 + BullMQ  
**AI** FastAPI (Python 3.11) — isolated `/predict /health /metrics`  
**Payments** Stripe (subscriptions + metered + Customer Portal)  
**Infra** Docker + GitHub Actions → Fly/Render or AWS/GCP, Sentry + OTEL

## Getting Started (local)
```bash
cp .env.example .env
docker compose up --build
# web  http://localhost:5173
# api  http://localhost:3000/api/v1  (/api/docs → OpenAPI)
# ai   http://localhost:8000/health
```

## Repo Structure
```
apps/web          # React + Vite
apps/api          # NestJS + Prisma
services/ai-service # FastAPI
packages/*        # shared-types, eslint-config
docs/             # architecture & runbooks
docker-compose.yml
.github/workflows/ci.yml
```

## Branches
- `develop` → auto deploys **staging**
- `main` → manual approve → **production**

## Milestones
Week 1-2 Scaffold+CI → 3-5 Auth+Tenant+AI health → 5-8 Frontend wired → 8-10 Stripe+Admin → 10-12 Hardening+Prod

## Contributing
See `docs/` — confirm Node vs Python backend and auth provider before large changes.
