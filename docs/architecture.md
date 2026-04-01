# Architecture Overview

## System Role

This service is the **AI processing middleware** for the spare parts B2B company.
It sits between the customer-facing CRM (Bitrix24) and the internal team (VK Teams).

```
Customer channels
  ├── Telegram
  ├── Email
  ├── MAX messenger
  └── Bitrix (web form, phone, etc.)
         │
         ▼  webhooks / events
┌─────────────────────────────┐
│   spare-parts-ai-backend    │
│                             │
│  1. Normalise inbound msg   │
│  2. Classify (LLM)          │──► PostgreSQL (request logs, audit trail)
│  3. Extract fields          │
│  4. Generate draft reply    │──► RAG (vector store, catalogue lookup)
│  5. Escalation decision     │
│  6. Notify team             │──► VK Teams (internal chat)
└─────────────────────────────┘
         │
         ▼  (post-MVP, after human approval)
   Bitrix / Telegram / Email  ──► Customer reply
```

---

## Layer Responsibilities

### `app/api/routes/`
HTTP boundary only. Routes parse incoming requests, optionally validate
a shared secret, and immediately delegate to the service layer.
No business logic. No direct DB access.

### `app/services/`
Business workflow owners. A service method represents one complete
business operation (e.g. "handle an incoming customer request").
Services coordinate repositories, agents, and notification — and own
transaction boundaries.

### `app/agents/`
Autonomous reasoning units. Each agent has a single responsibility
and communicates with the LLM via `app/llm/client.py`.
Agents do not talk to the DB or external APIs directly.

- `ClassifierAgent` — categorise + extract fields
- `ResponderAgent` — generate draft reply
- `Orchestrator` — coordinate multiple agents per request

### `app/llm/`
LLM API abstraction. All agents call `llm_client.chat()` — never
httpx directly. Handles retry, JSON extraction, schema validation.

### `app/prompts/`
Prompt templates. Separated from agent logic so they can be iterated
without touching Python code. Each prompt is a class with a `build()` method.

### `app/rag/`
Retrieval-Augmented Generation. Not active in MVP.
Will retrieve relevant catalogue entries to ground LLM responses
in real part data, preventing hallucination of specifications.

### `app/integrations/`
External service clients. One file per service.
Each integration has a single concern: talk to one external API.
No business logic — that belongs in services.

### `app/db/`
Database access layer.
- `models.py` — SQLAlchemy ORM table definitions
- `session.py` — async engine + FastAPI DI session factory
- `repositories/` — typed data-access methods (no raw SQL in services)

### `app/core/`
Shared domain types used across layers.
- `schemas.py` — IncomingRequest, PipelineResult, enums
- `exceptions.py` — typed exception hierarchy

### `app/config/`
Typed configuration via pydantic-settings.
All secrets and environment-specific values go here.

### `app/utils/`
Stateless helper functions with no business logic dependency.
Retry decorators, text utilities, etc.

---

## Data Flow (per request)

```
1. Bitrix webhook POST → routes/webhooks.py
2. Payload parsed → integrations/bitrix.py → IncomingRequest
3. RequestService.handle_incoming(request)
4.   → RequestRepository.create(request)          [persist raw]
5.   → Orchestrator.process(request)
6.       → ClassifierAgent.run(request)
7.           → ClassificationPrompt.build(text)
8.           → llm_client.chat(messages)           [LLM call]
9.           → parser.extract_json + validate()    [schema check]
10.          → ClassificationResult
11.      → [if spare_part] RAG.retrieve(query)     [future]
12.      → ResponderAgent.run(classification)
13.          → llm_client.chat(messages)            [LLM call]
14.          → DraftReply
15.      → PipelineResult
16.  → RequestRepository.save_classification(result)
17.  → NotificationService.notify_team(result)
18.      → VKTeamsClient.send_text(message)
19. → Return WebhookResponse to Bitrix
```

---

## Database Schema (planned)

| Table | Purpose |
|---|---|
| `request_logs` | Master record per inbound request |
| `classification_logs` | LLM output — category, confidence, draft |
| `processing_events` | Append-only audit trail |

Vector store (pgvector or Qdrant):
| Collection | Purpose |
|---|---|
| `catalogue_parts` | Spare parts with embeddings for RAG retrieval |

---

## Scalability Notes

- **Horizontal scaling**: the service is stateless — run N replicas behind a load balancer
- **Async queue**: webhook endpoints should enqueue work (Celery/ARQ) rather than processing inline, to handle traffic spikes without timeouts
- **Multi-agent expansion**: the Orchestrator pattern supports adding new agents (EscalationAgent, PartSelectionAgent) without changing existing agents
- **Multi-tenant**: add `company_id` to all tables and route configs to support multiple Bitrix portals
