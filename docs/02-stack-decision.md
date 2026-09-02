# Stack Decision Table — Audit & Rationale

> Audit date: 2026-09-02. Repo at audit: single README, no `package.json`, no `Dockerfile`, no `requirements.txt`. Treated as greenfield. Preserved assets: N/A (no legacy code to extract). This table doubles as Keep/Refactor/Replace log.

## 1. Inventory (actual)
| Artifact | Found | Verdict |
|----------|-------|---------|
| package.json / pnpm-workspace | ❌ | Create fresh monorepo |
| requirements.txt / pyproject.toml | ❌ | Create for ai-service |
| Dockerfile / compose | ❌ | Create multi-service |
| CI config | ❌ | Create GitHub Actions |
| .env.example | ❌ | Create validated |
| DB schema | ❌ | Design new (see 03-database) |
| Model weights / prompts | ❌ | Placeholder contract, bring your model |

## 2. Stack Decision Table
| Layer | Choice | Keep / Replace | Justification |
|-------|--------|----------------|---------------|
| Frontend | React 18 + TS + Vite, Tailwind, shadcn/ui | Replace (new) | Fast DX, huge hiring pool, shadcn covers SaaS dashboard patterns; Vite fast HMR |
| State | TanStack Query + Zustand | New | No Redux boilerplate; clear server vs client split |
| Backend | NestJS (Node 20) | New | Structured, DI, guards/interceptors, testable; fits SaaS backend needs. **Swap to FastAPI** if team is Python-native/AI-heavy — single language wins (document swap) |
| DB | PostgreSQL 16 + Prisma | New | Relational integrity for tenants/billing; Prisma type-safe migrations |
| Auth | JWT access(15m)+refresh(7d httpOnly) + RBAC; or Clerk/Auth0 | New | Self-roll keeps costs low; managed saves weeks — gated by `AUTH_PROVIDER` flag |
| AI inference | FastAPI microservice (Python 3.11) | New | Always isolate ML deps; scale/GPU separately; contract `/predict /health /metrics` |
| Queue | Redis 7 + BullMQ | New | Metering, async AI jobs, webhooks; Celery if backend is FastAPI-only |
| Payments | Stripe Billing + Metered Usage + Customer Portal | New | Industry default; subs + metered + invoices + dunning natively |
| Infra | Docker + GH Actions → Fly/Render or AWS/GCP | New | Single pipeline, reproducible, staging+prod with approval gate |
| Monitoring | Sentry (errors) + OTEL → Grafana/Datadog | New | Required for prod-grade claims; traces + metrics from day 1 |

## 3. Tradeoffs Flagged
- **Node vs Python backend**: If AI logic dominates (>60% code) and team is Python-native, use FastAPI end-to-end (backend+AI). Else NestJS+separate FastAPI keeps FE/BE in TS. Decide before scaffold — one-line rationale in this file.
- **Managed Auth**: Clerk/Auth0 saves ~2 weeks but adds $/tenant. Self-roll cheaper but needs refresh rotation, breach handling. Default self-roll, flip via env.
- **Row-level tenancy**: Ships fastest; schema-per-tenant only if tenant demands physical isolation/GDPR. Migration path documented in 03-database.
- **Monorepo**: pnpm workspaces + Turborepo (optional). Alternative: separate repos — more overhead, not needed at this scale.

## 4. Version Pins (v1)
Node 20 LTS, pnpm 9, Python 3.11, Postgres 16, Redis 7, Prisma 5, NestJS 10, FastAPI 0.110, React 18.3, Vite 5, Tailwind 3.4.

## 5. Confirm Before Scaffold
- [ ] Confirm backend language (NestJS vs FastAPI) — default NestJS
- [ ] Confirm auth provider (self JWT vs Clerk/Auth0)
- [ ] Confirm cloud target (Fly/Render vs AWS/GCP) — affects IaC
- [ ] Provide model artifact location / API contract if reusing existing model
