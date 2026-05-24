# scripts/

Operational Python scripts that run *outside* the FastAPI request loop.
Each script imports from `apps/api/app/` to reuse the same models and
LLM clients.

Planned (Week 2-3):

- `seed_tenants.py` — initial insert of LV Trade + Equipart rows
- `seed_lvtrade.py` — load LV Trade catalog from iCloud Excel files
- `seed_equipart.py` — load Equipart catalog from `equipart-shop/lvtrade-import-staging/`
- `import_catalog.py` — generic Excel/CSV → products
- `seed_error_codes.py` — per-tenant error-code library loader
- `generate_embeddings.py` — backfill Pinecone for a tenant
- `create_tenant.py`, `create_admin.py`, `send_welcome.py`

Run with the API venv active:

```bash
cd apps/api
source .venv/bin/activate
python ../../scripts/seed_lvtrade.py
```
