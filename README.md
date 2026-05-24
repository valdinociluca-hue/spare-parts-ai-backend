# PartsAI

Multi-tenant AI platform for spare-parts distributors in the HoReCa /
equipment industry. First two tenants: **LV Trade** (Russia, YandexGPT)
and **Equipart** (global, Claude).

## Modules

| # | Module | Phase |
|---|--------|-------|
| 1 | AI Parts Identification | 1 (current) |
| 2 | AI Technician Assistant | 1 (current) |
| 3 | AI Order Assistant | 1 (current) |
| 4 | AI Documentation Search | 2 |
| 5 | AI Service Copilot (mobile) | 3 |
| 6 | Predictive Maintenance | 3 |

## Monorepo layout

```
apps/
  web/        Next.js 14 dashboard + customer chat (Vercel)
  api/        FastAPI backend (Railway)
  widget/     Embeddable vanilla-JS chat widget
packages/
  shared/     Shared TypeScript types
  ui/         shadcn/ui-based component library
  eslint-config/
supabase/
  migrations/ SQL migrations
  seed.sql    Seed for the two pre-configured tenants
scripts/      Tenant onboarding + catalog import scripts (Python)
docs/         ARCHITECTURE, ADDING_TENANT, DEPLOYMENT, ROADMAP
legacy/       Original single-app FastAPI code (pre-rewrite, kept for reference)
```

## Local dev

Requires: Node ≥20, pnpm ≥10, Python ≥3.11, Docker.

```bash
pnpm install
docker compose up -d              # local Postgres on :54322
cp .env.example .env              # fill in real keys when provisioned
pnpm dev                          # turbo runs all apps in parallel
```

Per-app dev:

```bash
pnpm --filter @partsai/web dev    # Next.js dashboard on :3000
pnpm --filter @partsai/api dev    # FastAPI on :8000 (delegates to uvicorn)
pnpm --filter @partsai/widget dev # widget bundle watcher on :3001
```

Apply migrations to the local DB:

```bash
psql "$DATABASE_URL" -f supabase/migrations/0001_init.sql
psql "$DATABASE_URL" -f supabase/seed.sql
```

## Multi-tenancy

Every database row carries `tenant_id`. Tenant is resolved from:

- **Dashboard:** subdomain (`<slug>.partsai.com`) → Next.js middleware
- **Widget:** public API key (`pk_live_<…>` on `<script data-key="…">`)
- **API:** JWT claim (`tenant_id`) issued by Supabase Auth

Backend `apps/api/app/deps.get_current_tenant` enforces isolation on
every request. Cross-tenant access is a tested invariant.

## Status

Week 1 in progress: monorepo skeleton, DB schema, API/web scaffolds, tenant middleware.
See `docs/ROADMAP.md` for the full 4-week sequence.
