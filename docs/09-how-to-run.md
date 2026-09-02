# How to Run — All Environments (Windows / Linux / macOS / BSD)

> Single Docker path works everywhere. Native per-OS paths below for bare-metal.

## 1. Prerequisites
| Tool | Version | Install |
|------|---------|---------|
| Node | 20 LTS | https://nodejs.org |
| pnpm | 9.x | `npm i -g pnpm` |
| Python | 3.11 | https://python.org |
| Docker Desktop | latest | https://docker.com (includes compose) — runs on Win/Mac/Linux/BSD via podman/colima |
| Git | latest | — |

Check: `node -v && pnpm -v && python --version && docker --version && docker compose version`

## 2. Clone & Env
```bash
git clone https://github.com/ajit-ai/Quantsmind-AI-SaaS-Full-Stack.git
cd Quantsmind-AI-SaaS-Full-Stack
cp .env.example .env          # Linux/macOS/BSD
# Windows PowerShell:
Copy-Item .env.example .env
# Edit .env: set JWT_ACCESS_SECRET/JWT_REFRESH_SECRET (32+ chars), Stripe keys if testing billing
```

Env vars (see `.env.example`): `DATABASE_URL`, `REDIS_URL`, `JWT_*`, `AI_SERVICE_URL`, `AI_SERVICE_TOKEN`/`INTERNAL_TOKEN`, `STRIPE_*`, `VITE_API_URL`, `CORS_ORIGINS`.

## 3. Run with Docker (recommended — same on all OS)
```bash
docker compose up --build
# detached: docker compose up --build -d && docker compose logs -f

# Services:
# web  http://localhost:5173  (nginx serving built React, proxies /api to api:3000)
# api  http://localhost:3000/api/v1         → health: /api/v1/health
#      Swagger: http://localhost:3000/api/docs  → exports docs/openapi.json
# ai   http://localhost:8000/health  (needs header X-Internal-Token: dev-internal-token for /predict)
# postgres  localhost:5432 (user quantsmind / pass quantsmind / db quantsmind)
# redis     localhost:6379

# Verify:
curl http://localhost:3000/api/v1/health
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -H "X-Internal-Token: dev-internal-token" -d '{"prompt":"hello"}'

# Stop & clean:
docker compose down        # keep volumes (pgdata/redisdata)
docker compose down -v    # also delete volumes
```

**Windows note:** Use PowerShell or WSL2; Docker Desktop handles line endings (CRLF→LF via `.gitattributes`). If `docker compose` not found, use `docker-compose`.

**BSD note:** Use `podman-compose` or `colima`, or run Linux containers via `docker` compat layer. Or use native path below.

## 4. Run Natively (without Docker) — per OS

### 4.1 Infra (postgres + redis) — all OS
```bash
# Option A: use Docker just for infra
docker compose up postgres redis -d
# Option B: install natively
# Linux (apt): sudo apt install postgresql-16 redis-server
# macOS (brew): brew install postgresql@16 redis && brew services start postgresql@16 && brew services start redis
# Windows: install PostgreSQL + Redis via installers, or WSL2
# BSD: pkg install postgresql16-server redis
```

### 4.2 API (NestJS) — all OS
```bash
cd apps/api
pnpm install
npx prisma generate          # generates engine for current OS (win32/linux/darwin/freebsd)
npx prisma migrate dev --name init   # or: npx prisma db push (dev)
pnpm dev                     # http://localhost:3000/api/v1/health (watch mode)
# prod: pnpm build && node dist/main.js
# Windows PowerShell: same commands; if argon2 build fails, install windows-build-tools / Visual Studio Build Tools
```

### 4.3 AI Service (FastAPI) — all OS
```bash
cd services/ai-service
python -m venv .venv
# Linux/macOS/BSD: source .venv/bin/activate
# Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000  # http://localhost:8000/health
# prod: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4.4 Web (React) — all OS
```bash
cd apps/web
pnpm install
pnpm dev   # http://localhost:5173 (Vite proxies /api to http://localhost:3000)
# prod: pnpm build && pnpm preview
```

## 5. Integration Test (web → api → ai → stripe mock)
```bash
# 1. Register
curl -X POST http://localhost:3000/api/v1/auth/register -H "Content-Type: application/json" -d '{"email":"a@ex.com","password":"Str0ng!123","tenantName":"Acme","slug":"acme"}'
# → {accessToken, tenant:{id}}

# 2. Predict (via api, which calls ai-service)
TOKEN=<accessToken>; TENANT=<tenantId>
curl -X POST http://localhost:3000/api/v1/ai/predict -H "Authorization: Bearer $TOKEN" -H "x-tenant-id: $TENANT" -H "Content-Type: application/json" -d '{"prompt":"Summarize Q2"}'
# → {requestId, result, cached:false, latencyMs: ~12 (mock)}

# 3. Usage
curl http://localhost:3000/api/v1/billing/usage -H "Authorization: Bearer $TOKEN" -H "x-tenant-id: $TENANT"

# 4. E2E (Playwright, once implemented)
pnpm test:e2e  # runs signup → predict → billing flow against compose
```

## 6. Per-OS Bundles (how to produce)
```bash
# Web (OS-agnostic, but zipped per OS for release)
pnpm --filter @quantsmind/web build && tar czf web-$(uname -s)-$(uname -m).tar.gz -C apps/web/dist .

# API (native per OS — must build on that OS runner for correct argon2/prisma engine)
pnpm --filter @quantsmind/api build && npx prisma generate
# Windows runner → api-windows-x64.zip, macOS → api-darwin-arm64.tar.gz, FreeBSD VM → api-bsd.tar.gz

# AI
pip install -r services/ai-service/requirements.txt && tar czf ai-$(uname -s).tar.gz services/ai-service/app

# Docker (universal, recommended prod — multi-arch)
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/ajit-ai/quantsmind-api:sha -f apps/api/Dockerfile . --push
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/ajit-ai/quantsmind-web:sha -f apps/web/Dockerfile . --push
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/ajit-ai/quantsmind-ai:sha -f services/ai-service/Dockerfile . --push
```

## 7. Troubleshooting
| Issue | Fix |
|-------|-----|
| `argon2` build fail on Windows | Install Visual Studio Build Tools + `npm i -g node-gyp`, or use Docker |
| `prisma generate` wrong engine | Run `npx prisma generate` on target OS; set `binaryTargets = ["native","linux-musl-arm64-openssl-3.0.x"]` in `schema.prisma` |
| Port 3000/5173/8000 in use | `lsof -i :3000` / `netstat -ano | findstr :3000` then kill, or change `PORT` in `.env` |
| CORS error | Set `CORS_ORIGINS=http://localhost:5173` in `.env` matching web origin |
| Stripe webhook 400 | Use `stripe listen --forward-to localhost:3000/api/v1/billing/webhook` + `STRIPE_WEBHOOK_SECRET` |

## 8. Next Steps
- See `docs/03-database-schema.md` for Prisma migrate/seed.
- See `docs/04-api-spec.md` for full endpoint list + OpenAPI.
- See `docs/07-infra-cicd.md` for CI/CD, GHCR, staging/prod deploy, monitoring.

Full pipeline: `feature/* → PR → develop (staging auto) → main (prod approval)` — `README.md`.
