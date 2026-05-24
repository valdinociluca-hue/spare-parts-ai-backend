# Architecture

```
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  Tenant site (e.g.   │   │ <slug>.partsai.com   │   │ admin.partsai.com    │
│  lvtrade.ru) loads   │   │ Tenant dashboard     │   │ Super-admin          │
│  widget.js           │   │ (apps/web)           │   │ (apps/web)           │
└──────────┬───────────┘   └──────────┬───────────┘   └──────────┬───────────┘
           │                          │                          │
           ▼                          ▼                          ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                  api.partsai.com (apps/api, FastAPI)                  │
  │  Tenant resolution: widget API key | JWT claim | X-Tenant-Slug header │
  │  Modules: /v1/parts (id+search) · /v1/chat · /v1/orders               │
  └─────────┬───────────────────┬──────────────────────┬───────────────────┘
            │                   │                      │
            ▼                   ▼                      ▼
   ┌────────────────┐  ┌────────────────┐    ┌────────────────────┐
   │ Supabase       │  │ Pinecone       │    │ LLM router         │
   │ Postgres + RLS │  │ vector index   │    │  ├── YandexGPT (RU)│
   │ + Auth + Blob  │  │ (per-tenant    │    │  └── Claude (GLOBAL)│
   │                │  │  namespace)    │    │ + OpenAI embeddings│
   └────────────────┘  └────────────────┘    └────────────────────┘
```

## Multi-tenancy invariants

1. Every table has `tenant_id UUID NOT NULL`.
2. Every API request resolves a tenant *before* any handler logic runs.
3. Every DB query in `apps/api/app/db/` accepts `tenant_id` and filters by it.
4. Supabase RLS provides defense-in-depth: even if a query forgets the filter, the row policy enforces isolation.
5. Pinecone uses `namespace=tenant_id` so vector search cannot leak cross-tenant.
6. A test suite (`apps/api/tests/test_tenant_isolation.py`) proves no API endpoint returns another tenant's data.

## Tenant resolution order (backend)

1. `X-Tenant-Slug` header — only honored when `Authorization: Bearer <service-role>` (internal scripts).
2. `widget_api_key` (query param or `X-Widget-Key` header) — looked up in `tenants.widget_api_key`. Used by the embedded widget.
3. `Authorization: Bearer <jwt>` — JWT issued by Supabase Auth, with `tenant_id` claim. Used by the dashboard.

`apps/api/app/deps.get_current_tenant` implements this order and 401s if no
tenant can be resolved.

## Module surface

| Module | Endpoint | Where |
|--------|----------|-------|
| 1. Parts ID | `POST /api/v1/parts/identify` | `apps/api/app/routers/parts.py` |
| 1. Parts search | `POST /api/v1/parts/search` | same |
| 2. Technician | `POST /api/v1/chat/technician` | `apps/api/app/routers/chat.py` |
| 3. Order | `POST /api/v1/orders/draft` | `apps/api/app/routers/orders.py` |

## LLM routing

`apps/api/app/llm/router.py::get_llm_for_tenant` returns a `BaseLLMClient`
implementation based on `tenant.llm_provider`. Both implementations
expose the same interface:

```python
class BaseLLMClient:
    async def chat(self, messages: list[Message], **kwargs) -> CompletionResponse: ...
    async def embed(self, text: str) -> list[float]: ...
```

Embeddings always go through OpenAI (`text-embedding-3-small`) regardless
of chat provider — Yandex embeddings exist but OpenAI is cheaper and
better at multilingual.
