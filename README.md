# spare-parts-ai-backend

AI processing middleware for a B2B HoReCa spare parts company.

Classifies customer requests (Bitrix, Telegram, email, MAX), extracts
key fields, generates draft replies, and routes to the internal team.

> **Status:** scaffold — business logic not yet implemented.
> See `docs/architecture.md` for the full design.

---

## Quick start

```bash
cp .env.example .env          # fill in LLM_API_KEY, VK_TEAMS_BOT_TOKEN, etc.
docker-compose up --build
curl http://localhost:8000/health
```

---

## Project structure

```
app/
  main.py             FastAPI app, lifespan, middleware, routes
  config/             Typed settings via pydantic-settings
  api/routes/         HTTP routes — thin, no business logic
  agents/             LLM-based reasoning units (classifier, responder, orchestrator)
  services/           Business workflow layer (request lifecycle, notifications)
  llm/                LLM client, JSON parser, output schemas
  prompts/            Prompt templates — editable without touching logic
  integrations/       External service clients (Bitrix, VK Teams, Telegram, email)
  rag/                Retrieval-augmented generation (embedder, retriever, vector store)
  db/
    models.py         SQLAlchemy ORM table definitions
    session.py        Async engine + FastAPI DI session factory
    repositories/     Typed data-access methods
  core/               Shared domain types (IncomingRequest, exceptions, enums)
  utils/              Stateless helpers (retry, text processing)

tests/
  unit/               Pure logic tests — no DB, no HTTP, no LLM
  integration/        FastAPI TestClient tests — mocked services

scripts/
  embed_catalogue.py  Index spare parts catalogue into vector store (RAG)
  seed_db.py          Seed development database with test data

docs/
  architecture.md     System design, data flow, scalability notes

docker/
  Dockerfile          Multi-stage production image
```

---

## Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest -v
```

---

## Configuration

All settings are in `app/config/settings.py` and read from environment variables.
See `.env.example` for the full list.
