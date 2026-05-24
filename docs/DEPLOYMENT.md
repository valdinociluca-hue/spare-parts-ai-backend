# Deployment

| Service | Target | How |
|---------|--------|-----|
| `apps/web` | Vercel | `git push` → auto-deploy on `main` |
| `apps/widget` | Vercel (static) | Build to CDN; `widget.partsai.com` |
| `apps/api` | Railway | Docker (`apps/api/Dockerfile`), `uvicorn app.main:app` |
| Postgres | Supabase | Managed; migrations applied via Supabase CLI |
| Vector DB | Pinecone | Managed; one index, per-tenant namespaces |
| Storage | Supabase Storage | For uploaded manuals/images |

## DNS

```
partsai.com           → Vercel marketing site (later)
api.partsai.com       → Railway (apps/api)
widget.partsai.com    → Vercel (apps/widget)
admin.partsai.com     → Vercel (apps/web with super-admin scope)
*.partsai.com         → Vercel (apps/web with tenant scope, resolved via subdomain)
```

## Promotion flow

1. PRs deploy preview URLs on Vercel and Railway automatically.
2. Merging to `main` triggers production deploys on both.
3. Schema changes go through Supabase CLI:
   ```bash
   supabase db push                   # apply pending migrations to prod
   ```
4. Pinecone index changes (rebuilding embeddings) run as one-off jobs:
   ```bash
   python scripts/generate_embeddings.py --tenant <slug> --rebuild
   ```

## Rollback

- `apps/web` / `apps/widget`: Vercel UI → "Rollback to previous deploy".
- `apps/api`: Railway UI → "Redeploy" a previous image.
- DB: never rollback schema in prod — write a forward migration that
  undoes the change.

## Secrets

All env vars live in:
- Vercel project settings (frontend)
- Railway project settings (backend)
- `.env` locally (never committed)

The `.env.example` at the monorepo root is the source of truth for which
vars exist; keep it in sync.
