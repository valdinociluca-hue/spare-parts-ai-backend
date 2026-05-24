# Tenant middleware — manual verification

Run `pnpm --filter @partsai/web dev` and verify in a browser:

| Hostname (set via `--host` or `/etc/hosts`) | Expected `X-PartsAI-Tenant-Slug` |
|---------------------------------------------|----------------------------------|
| `localhost:3000`                            | `NEXT_PUBLIC_DEFAULT_TENANT_SLUG` (`lvtrade`) |
| `lvtrade.partsai.local:3000`                | `lvtrade`                        |
| `equipart.partsai.local:3000`               | `equipart`                       |
| `admin.partsai.local:3000`                  | (none — reserved, passes through) |
| `random.partsai.local:3000`                 | `random` (API returns 404 → home page renders "No tenant resolved") |

To test subdomains locally, add to `/etc/hosts`:

```
127.0.0.1 lvtrade.partsai.local equipart.partsai.local admin.partsai.local
```

Set `NEXT_PUBLIC_APP_DOMAIN=partsai.local` in `.env`.

Automated tests with Playwright land alongside the dashboard in Week 3 step 13.
