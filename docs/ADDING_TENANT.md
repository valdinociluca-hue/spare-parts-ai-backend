# Adding a tenant

> Self-serve signup is intentionally not built in Phase 1.
> Onboarding is manual for the first 5 customers.

## Step-by-step

```bash
# 1. Create the tenant row + widget API key
python scripts/create_tenant.py \
  --slug equipart \
  --name "Equipart" \
  --region GLOBAL \
  --llm claude \
  --brand-color "#2E7D32" \
  --language en

# 2. Import the catalog (Excel/CSV → products table)
python scripts/import_catalog.py \
  --tenant equipart \
  --file /path/to/equipart_catalog.xlsx

# 3. Seed error codes
python scripts/seed_error_codes.py \
  --tenant equipart \
  --file /path/to/equipart_error_codes.json

# 4. Generate embeddings (OpenAI → Pinecone, namespace=tenant_id)
python scripts/generate_embeddings.py --tenant equipart

# 5. Create the first admin user (Supabase magic link)
python scripts/create_admin.py \
  --tenant equipart \
  --email admin@equipart.com

# 6. Send welcome email with widget embed code + dashboard URL
python scripts/send_welcome.py --tenant equipart
```

## Acceptance check

After onboarding, verify in `<slug>.partsai.com`:

- Dashboard loads with the tenant's brand color and logo
- `/catalog` shows the imported products
- `/conversations` is empty
- `/settings/widget` shows a copy-paste `<script>` tag

Then verify the widget on a sandbox HTML page:

- Floating button appears in the configured corner
- Sending a message reaches `/api/v1/parts/identify`
- Response references the correct catalog (no cross-tenant SKUs)

## Cost ceiling

Document the tenant's expected monthly LLM spend per plan tier. PartsAI
bills on top of LLM cost; the `usage_log` table tracks every call.
