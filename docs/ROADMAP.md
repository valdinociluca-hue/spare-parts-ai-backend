# PartsAI Roadmap

## Phase 1 — Modules 1-3 (current)

### Week 1 — Foundations
1. ✅ Monorepo skeleton (Turborepo + pnpm)
2. ✅ Database schema (SQL migrations)
3. ✅ FastAPI scaffold (`apps/api`)
4. ✅ Next.js scaffold (`apps/web`)
5. ✅ Tenant middleware (backend + frontend)

### Week 2 — Module 1: AI Parts Identification
6. LLM router (Yandex + Claude with shared `BaseLLMClient`)
7. Product import script (`scripts/seed_lvtrade.py`)
8. Embeddings pipeline (OpenAI → Pinecone, filtered by `tenant_id`)
9. Module 1 API + integration tests
10. Widget v1 — floating button, chat panel, product cards

### Week 3 — Modules 2 & 3
11. Module 2: Technician Assistant (error-code regex + diagnostic tree)
12. Module 3: Order Assistant (intent parsing, cross-sell)
13. Dashboard pages: catalog editor, conversations, settings
14. Super-admin: tenant management

### Week 4 — Production
15. Polish, error handling, monitoring (Sentry / Vercel observability)
16. Deploy LV Trade to production
17. Document onboarding (`docs/ADDING_TENANT.md`)
18. Onboard Equipart as second tenant — validates multi-tenancy

## Stop after Phase 1

Phase 2 (Documentation Search) and Phase 3 (Service Copilot mobile,
Predictive Maintenance) do not start until LV Trade and Equipart are
live and actively used.

## Success criteria

- LV Trade customers chat at `lvtrade.partsai.com` and get instant SKU answers
- Widget embeds on `lvtrade.ru` with one `<script>` tag
- Equipart fully isolated from LV Trade — different LLM, different catalog
- Adding a third tenant takes < 1 hour
- Parts ID response < 3 seconds
- Russian text throughout LV Trade tenant (no translation artifacts)
