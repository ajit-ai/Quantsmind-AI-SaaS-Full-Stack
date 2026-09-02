# Consolidated Prompt — Copy-Paste for Agent / Freelancer

> Copy the block below alone when handing to Claude Code, Codex, freelancer, or job post.

````
You are rebuilding an AI-powered SaaS application from scratch. Deliver a modern,
production-grade full-stack system across four areas: Frontend, Backend, AI model
service, and SaaS infrastructure.

CONTEXT
- Prior codebase exists but is fragmented and poorly documented; treat this as a
  fresh build, but first extract and preserve: trained model artifacts, DB schema/
  business rules, and any existing user data before discarding old code.

STACK (confirm or override with justification before starting)
- Frontend: React 18 + TypeScript + Vite, Tailwind CSS, shadcn/ui, React Query, Zustand
- Backend: NestJS (Node/TypeScript) OR FastAPI (Python) — pick one, single language
  across backend + AI service if possible
- Database: PostgreSQL with Prisma or SQLAlchemy, migrations tracked in version control
- AI inference: standalone FastAPI microservice, versioned API contract, independent
  scaling from main backend
- Auth: JWT (access + refresh) with RBAC, or managed provider (Clerk/Auth0)
- Payments: Stripe (Subscriptions + Customer Portal + metered usage billing)
- Infra/CI: Docker, GitHub Actions, staging + production environments, one pipeline
- Monitoring: Sentry + metrics/tracing (OpenTelemetry or equivalent)

REQUIREMENTS
1. Frontend: responsive, mobile-first, modern SaaS UI (dashboard, auth, onboarding,
   billing/usage screens, admin panel), componentized and documented.
2. Backend: RESTful (OpenAPI-documented) API, input validation, rate limiting,
   role-based access control, unit + integration + E2E test coverage, CI/CD pipeline.
3. AI service: isolated inference microservice with health/metrics endpoints,
   documented latency and accuracy baseline vs. target, caching/batching where useful.
4. SaaS layer: multi-tenant data model (tenant_id row-level isolation as default),
   Stripe subscription + metered usage integration, usage event logging, admin
   dashboard with tenant/usage/revenue visibility.

DELIVERABLES
1. Audit note (only if legacy code is reused for data/model/schema) + stack decision
   rationale.
2. Fully documented, tested code for frontend, backend, and AI service.
3. Deployed staging environment demonstrating all core flows.
4. Production build with SaaS features live, monitoring configured, single CI/CD
   pipeline deploying to the target cloud account.

ACCEPTANCE CRITERIA
- All critical user flows (signup, core AI action, subscription/billing) pass
  automated E2E tests.
- AI inference meets an agreed latency target (state the number once benchmarked).
- One CI/CD pipeline deploys frontend, backend, and AI service to the target cloud
  account without manual steps beyond approval gates.

Work incrementally: scaffold → core auth/tenant model → AI inference service →
core product feature → billing integration → admin dashboard → hardening
(tests, monitoring, docs) → staging → production cutover. Confirm assumptions
about ambiguous requirements before large architectural commitments, and flag
any tradeoff (e.g., Node vs Python backend) with a one-line rationale rather
than silently picking one.
````

## Milestones (suggested)
1. **Week 1–2:** Audit complete, stack finalized, repo scaffolded, CI skeleton running.
2. **Week 3–5:** Core backend (auth, multi-tenant schema) + AI inference service live with health checks.
3. **Week 5–8:** Frontend core flows wired to backend; staging live.
4. **Week 8–10:** Stripe billing + usage metering + admin dashboard.
5. **Week 10–12:** Test hardening, monitoring, perf tuning vs latency target, production launch.

> Timelines assume 1–2 full-stack + 1 ML engineer; adjust after first sprint.
