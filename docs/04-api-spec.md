# API Spec — REST + OpenAPI (Backend at `/api/v1`, AI Service at `/ai`)

> Full spec generated via `@nestjs/swagger` at `/api/docs` → exported to `docs/openapi.json` in CI.

## 1. Conventions
- Base: `/api/v1`
- Auth: `Authorization: Bearer <accessToken>`; refresh via `POST /auth/refresh` (httpOnly cookie)
- Tenant: `x-tenant-id` header or JWT `tenantId`; mismatch → 403
- Errors: RFC7807 `application/problem+json` `{type, title, status, detail, instance, errors?}`
- Pagination: `?page=1&limit=20` → `{data, meta:{page, limit, total, totalPages}}`
- Idempotency: `Idempotency-Key` header for `POST /ai/predict` and Stripe calls
- Rate limit headers: `X-RateLimit-Limit / Remaining / Reset`

## 2. Endpoints
### Auth
| Method | Path | Auth | Desc |
|--------|------|------|------|
| POST | /auth/register | no | create user+tenant |
| POST | /auth/login | no | returns access+refresh |
| POST | /auth/refresh | refresh | rotate tokens |
| POST | /auth/logout | yes | revoke refresh |
| GET | /auth/me | yes | current user+tenants |
| POST | /auth/forgot-password | no | send reset |
| POST | /auth/reset-password | no | with token |

### Tenants & Membership
| POST | /tenants | yes | create tenant (owner) |
| GET | /tenants/:id | yes | get tenant |
| PATCH | /tenants/:id | owner/admin | update |
| GET | /tenants/:id/members | yes | list members |
| POST | /tenants/:id/invite | admin | invite member |
| PATCH | /tenants/:id/members/:uid | admin | change role |
| DELETE | /tenants/:id/members/:uid | admin | remove |

### AI
| POST | /ai/predict | yes | enqueue/cache → `{requestId, result, cached, latencyMs}` |
| GET | /ai/requests | yes | list own requests (paginated) |
| GET | /ai/requests/:id | yes | detail |

### Billing (Stripe)
| POST | /billing/checkout | owner | create Checkout Session → `url` |
| POST | /billing/portal | owner | Customer Portal `url` |
| GET | /billing/subscription | yes | current subscription |
| POST | /billing/webhook | stripe sig | handle `customer.subscription.*`, `invoice.*` |
| GET | /billing/usage | yes | current period usage chart data |

### Admin (super_admin)
| GET | /admin/tenants | super | list all tenants + plan + MRR |
| GET | /admin/tenants/:id | super | detail + usage |
| POST | /admin/impersonate | super | returns scoped token (audited) |
| GET/PUT | /admin/flags | super | feature flags |

### Health
| GET | /health | no | `{status, uptime, db, redis, ai}` |
| GET | /health/ready | no | k8s readiness |
| GET | /health/live | no | k8s liveness |

## 3. AI Service (internal, FastAPI) — `http://ai-service:8000`
| POST | /predict | `{"prompt":str, "params":obj, "modelVersion":str}` → `{"result":str, "tokensIn":int, "tokensOut":int}` |
| GET | /health | `{"status":"ok", "modelLoaded":bool, "version":str}` |
| GET | /metrics | Prometheus text |
| POST | /batch/predict | batch array |

- Auth: internal `X-Internal-Token` (shared secret) — not exposed publicly.
- Contract versioned via `modelVersion`; breaking change → new route `/v2/predict`.

## 4. Validation & Rate Limits
- All bodies validated via `class-validator`/`zod` → 400 with `errors` array.
- Throttler: 60 req/min per IP + 120 req/min per tenant for `/ai/predict` (Redis). Exceed → 429 + `Retry-After`.
- Input sanitize: prompt max 8k chars, strip control chars.

## 5. Example Flows
### Register → Login
```http
POST /api/v1/auth/register
{"email":"a@ex.com","password":"Str0ng!","tenantName":"Acme","slug":"acme"}
→ 201 {"user":{"id":"..."},"tenant":{"id":"...","slug":"acme"},"accessToken":"..."}
```

### Predict (cached)
```http
POST /api/v1/ai/predict
Authorization: Bearer ...
x-tenant-id: <tenantId>
Idempotency-Key: 550e8400-...
{"prompt":"Summarize Q2 revenue", "params":{"temperature":0.2}}
→ 200 {"requestId":"...","result":"...","cached":false,"latencyMs":612}
→ repeat same prompt quickly → 200 {"cached":true,"latencyMs":12}
```

## 6. OpenAPI Generation
- Decorators: `@ApiTags`, `@ApiBearerAuth`, `@ApiResponse` on every controller.
- CI step: `pnpm --filter api openapi:export` → commits `docs/openapi.json` if changed.
