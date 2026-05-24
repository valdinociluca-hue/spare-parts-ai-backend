# Legacy code (pre-monorepo)

This folder contains the original single-app FastAPI implementation of
`spare-parts-ai-backend` from before the multi-tenant PartsAI rewrite
that began on **2026-05-24**.

It is **not built or deployed** by the monorepo's Turborepo pipeline. It is
preserved here so we can mine:

- **`app/llm/yandex.py`** — working YandexGPT client
- **`app/llm/anthropic_client.py`** — Claude client
- **`app/tools/error_code_search.py`** — error-code matching logic
- **`app/rag/`** — embedding + retrieval scaffolding
- **`app/agents/`** — agent orchestration patterns
- **`scripts/seed_error_codes.py`** — error-code seed data shape

When the corresponding modules are built fresh under `apps/api/`, pull
the equivalent code from here, modernize it for the multi-tenant model
(every query filtered by `tenant_id`), and then this folder can be
deleted.

## How to run the legacy app (if needed for reference)

```bash
cd legacy
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker-compose up -d
uvicorn app.main:app --reload
```

Note: the legacy `.env.example` is at the **monorepo root** (not in this
folder) because it was already there at the time of the rewrite and the
new monorepo `.env.example` will eventually replace it.
