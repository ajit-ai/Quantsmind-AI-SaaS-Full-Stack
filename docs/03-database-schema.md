# Database Schema — PostgreSQL + Prisma (Multi-Tenant Row-Level)

## 1. ER Diagram (text)
```
Tenant 1──* Membership *──1 User
  │ 1            │
  │              │ (role: owner|admin|member)
  *──────────────┘
  │ 1
  ├──* AiRequest ──* UsageEvent
  ├──* Subscription (stripeSubscriptionId)
  ├──* Invoice
  ├──* ApiKey
  └──* AuditLog

User 1──* RefreshToken
User 1──* AiRequest
```

## 2. Prisma Schema (canonical, at `apps/api/prisma/schema.prisma`)
```prisma
datasource db { provider = "postgresql"; url = env("DATABASE_URL") }
generator client { provider = "prisma-client-js" }

enum Role { owner admin member }
enum Plan { free pro enterprise }
enum SubStatus { incomplete active past_due canceled trialing }

model Tenant {
  id        String   @id @default(cuid())
  name      String
  slug      String   @unique
  plan      Plan     @default(free)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  memberships Membership[]
  aiRequests  AiRequest[]
  subscriptions Subscription[]
  usageEvents UsageEvent[]
  apiKeys     ApiKey[]
  auditLogs   AuditLog[]
}

model User {
  id           String   @id @default(cuid())
  email        String   @unique
  passwordHash String?  // null if OIDC
  name         String?
  createdAt    DateTime @default(now())
  memberships  Membership[]
  refreshTokens RefreshToken[]
  aiRequests   AiRequest[]
}

model Membership {
  id       String @id @default(cuid())
  role     Role   @default(member)
  userId   String
  tenantId String
  user     User   @relation(fields: [userId], references: [id], onDelete: Cascade)
  tenant   Tenant @relation(fields: [tenantId], references: [id], onDelete: Cascade)
  @@unique([userId, tenantId])
  @@index([tenantId])
}

model RefreshToken {
  id        String   @id @default(cuid())
  tokenHash String   @unique
  userId    String
  expiresAt DateTime
  revokedAt DateTime?
  user      User @relation(fields: [userId], references: [id], onDelete: Cascade)
}

model AiRequest {
  id           String   @id @default(cuid())
  tenantId     String
  userId       String
  modelVersion String   @default("v1")
  promptHash   String
  prompt       String   @db.Text
  result       Json?
  tokensIn     Int?
  tokensOut    Int?
  latencyMs    Int?
  cached       Boolean  @default(false)
  createdAt    DateTime @default(now())
  tenant Tenant @relation(fields: [tenantId], references: [id])
  user   User   @relation(fields: [userId], references: [id])
  @@index([tenantId, createdAt])
  @@index([promptHash])
}

model UsageEvent {
  id        String   @id @default(cuid())
  tenantId  String
  metric    String   // e.g. ai_calls, tokens
  quantity  Int      @default(1)
  idempotencyKey String @unique
  createdAt DateTime @default(now())
  tenant Tenant @relation(fields: [tenantId], references: [id])
  @@index([tenantId, createdAt])
}

model Subscription {
  id                   String    @id @default(cuid())
  tenantId             String
  stripeCustomerId     String
  stripeSubscriptionId String    @unique
  stripePriceId        String
  status               SubStatus
  currentPeriodEnd     DateTime?
  tenant Tenant @relation(fields: [tenantId], references: [id])
}

model ApiKey {
  id        String   @id @default(cuid())
  tenantId  String
  keyHash   String   @unique
  name      String
  lastUsedAt DateTime?
  createdAt DateTime @default(now())
  tenant Tenant @relation(fields: [tenantId], references: [id])
}

model AuditLog {
  id        String   @id @default(cuid())
  tenantId  String?
  userId    String?
  action    String
  target    String?
  meta      Json?
  createdAt DateTime @default(now())
  tenant Tenant? @relation(fields: [tenantId], references: [id])
  @@index([tenantId, createdAt])
}

model FeatureFlag {
  key       String  @id
  enabled   Boolean @default(false)
  tenantId  String? // null = global
}
```

## 3. Multi-Tenancy Enforcement
- Prisma extension `tenantExtension(tenantId)` injects `where: { tenantId }` for tenant-scoped models.
- Migration: `@@index([tenantId])` everywhere; RLS (Row Level Security) optional Postgres policy for defense-in-depth (future).
- Super admin reads cross-tenant only via `admin` module with audit log.

## 4. Migrations & Seed
- `prisma migrate dev --name init` / `migrate deploy` in CI
- Seed: 1 tenant `demo`, 1 owner `owner@demo.test / password123`, Stripe price stubs

## 5. Metering Reconciliation
- `UsageEvent.idempotencyKey = sha256(tenantId + aiRequestId)` prevents double count on retries.
- Worker aggregates `sum(quantity) WHERE createdAt in billingPeriod` hourly, pushes to Stripe `subscription_items.createUsageRecord`.
- Drift check job compares `UsageEvent` sum vs Stripe usage — alert if >0.1%.

## 6. Future Evolution
- Schema-per-tenant: move `tenantId` → schema name via `SET search_path`; requires migration script.
- Partition `AiRequest`/`UsageEvent` by `createdAt` monthly when >10M rows.
