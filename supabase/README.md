# supabase/

Database migrations and seed data.

## Apply to local Postgres

`docker compose up -d` mounts `migrations/` and `seed.sql` into the
Postgres init dir, so a fresh container picks them up automatically.

To re-apply against an already-running container:

```bash
psql "$DATABASE_URL" -f supabase/migrations/0001_init.sql
psql "$DATABASE_URL" -f supabase/seed.sql
```

## Apply to Supabase (production)

```bash
supabase link --project-ref <project-ref>
supabase db push
```

## Naming convention

`NNNN_short_description.sql` — strictly increasing, never edit a
migration after it has been applied anywhere. New schema changes = new
migration file.

## RLS

Row-level security is enabled on every tenant-scoped table.
`current_tenant_id()` is the trust boundary — it reads from:

1. Supabase JWT claim `tenant_id` (dashboard + widget paths via Supabase)
2. Postgres GUC `partsai.tenant_id` (FastAPI sets via `set_config`)

The FastAPI app's `apps/api/app/deps.get_current_tenant` is responsible
for setting the GUC before any query runs.
