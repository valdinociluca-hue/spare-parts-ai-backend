-- ─────────────────────────────────────────────────────────────
-- PartsAI initial schema (Phase 1)
-- Multi-tenant: every business table carries tenant_id NOT NULL.
-- ─────────────────────────────────────────────────────────────

create extension if not exists "pgcrypto";  -- gen_random_uuid

-- ── current_tenant_id() ──
-- Returns the active tenant for the current request, in priority order:
--   1. Supabase JWT claim 'tenant_id'   (production / dashboard / widget)
--   2. session GUC 'partsai.tenant_id'  (FastAPI sets this per request)
-- Returns NULL if neither is set; RLS policies treat that as "no access".
create or replace function public.current_tenant_id()
returns uuid
language plpgsql
stable
as $$
declare
  jwt_tenant text;
  guc_tenant text;
begin
  begin
    jwt_tenant := current_setting('request.jwt.claims', true)::json->>'tenant_id';
  exception when others then
    jwt_tenant := null;
  end;
  if jwt_tenant is not null and jwt_tenant <> '' then
    return jwt_tenant::uuid;
  end if;

  begin
    guc_tenant := current_setting('partsai.tenant_id', true);
  exception when others then
    guc_tenant := null;
  end;
  if guc_tenant is not null and guc_tenant <> '' then
    return guc_tenant::uuid;
  end if;

  return null;
end;
$$;

-- ── TENANTS ──
create table public.tenants (
  id              uuid primary key default gen_random_uuid(),
  slug            text unique not null,
  name            text not null,
  region          text not null check (region in ('RU','GLOBAL')),
  llm_provider    text not null check (llm_provider in ('yandex','claude')),
  brand_color     text not null default '#000000',
  logo_url        text,
  language        text not null default 'en',
  widget_api_key  text unique not null,
  plan            text not null default 'starter' check (plan in ('starter','pro','enterprise')),
  created_at      timestamptz not null default now()
);

-- ── TENANT USERS (dashboard admins) ──
create table public.tenant_users (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenants(id) on delete cascade,
  email       text not null,
  role        text not null default 'admin' check (role in ('admin','viewer')),
  created_at  timestamptz not null default now(),
  unique (tenant_id, email)
);
create index idx_tenant_users_tenant on public.tenant_users(tenant_id);

-- ── PRODUCTS (catalog per tenant) ──
create table public.products (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references public.tenants(id) on delete cascade,
  sku                 text not null,
  name                text,
  description         text,
  brand               text,
  category            text,
  compatible_models   text[] not null default '{}',
  qty_stock           numeric not null default 0,
  price_base          numeric,
  currency            text not null default 'RUB',
  embedding_id        text,
  metadata            jsonb,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (tenant_id, sku)
);
create index idx_products_tenant   on public.products(tenant_id);
create index idx_products_brand    on public.products(tenant_id, brand);
create index idx_products_category on public.products(tenant_id, category);

-- ── ERROR CODES ──
create table public.error_codes (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references public.tenants(id) on delete cascade,
  brand           text not null,
  model_pattern   text,
  error_code      text not null,
  description     text,
  likely_parts    text[] not null default '{}',
  severity        text check (severity in ('low','medium','high','critical')),
  solution        text
);
create index idx_error_codes_tenant on public.error_codes(tenant_id, brand, error_code);

-- ── CHAT SESSIONS ──
create table public.chat_sessions (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references public.tenants(id) on delete cascade,
  session_token   text unique not null,
  client_id       text,
  client_ip       text,
  user_agent      text,
  module          text not null default 'parts_id' check (module in ('parts_id','technician','order')),
  created_at      timestamptz not null default now(),
  last_activity   timestamptz not null default now()
);
create index idx_chat_sessions_tenant on public.chat_sessions(tenant_id, last_activity desc);

-- ── CHAT MESSAGES ──
create table public.chat_messages (
  id              uuid primary key default gen_random_uuid(),
  session_id      uuid not null references public.chat_sessions(id) on delete cascade,
  tenant_id       uuid not null references public.tenants(id) on delete cascade,
  role            text not null check (role in ('user','assistant','system')),
  content         text not null,
  skus_mentioned  text[] not null default '{}',
  module          text check (module in ('parts_id','technician','order')),
  tokens_used     integer,
  llm_provider    text check (llm_provider in ('yandex','claude')),
  created_at      timestamptz not null default now()
);
create index idx_chat_messages_session on public.chat_messages(session_id, created_at);
create index idx_chat_messages_tenant  on public.chat_messages(tenant_id, created_at desc);

-- ── ORDERS (Module 3 draft surface) ──
create table public.orders (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenants(id) on delete cascade,
  session_id  uuid references public.chat_sessions(id) on delete set null,
  client_id   text,
  items       jsonb not null,
  total       numeric,
  status      text not null default 'draft' check (status in ('draft','submitted','confirmed')),
  created_at  timestamptz not null default now()
);
create index idx_orders_tenant on public.orders(tenant_id, created_at desc);

-- ── USAGE LOG (per-tenant billing telemetry) ──
create table public.usage_log (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenants(id) on delete cascade,
  event_type  text not null,
  tokens_used integer,
  cost_cents  numeric,
  metadata    jsonb,
  created_at  timestamptz not null default now()
);
create index idx_usage_log_tenant on public.usage_log(tenant_id, created_at desc);

-- ── Row-level security ──
alter table public.tenants        enable row level security;
alter table public.tenant_users   enable row level security;
alter table public.products       enable row level security;
alter table public.error_codes    enable row level security;
alter table public.chat_sessions  enable row level security;
alter table public.chat_messages  enable row level security;
alter table public.orders         enable row level security;
alter table public.usage_log      enable row level security;

-- Tenants table: each tenant can only see its own row.
create policy tenant_self_select on public.tenants
  for select using (id = public.current_tenant_id());

-- All other business tables: read/write scoped to current_tenant_id().
create policy tenant_users_isolation on public.tenant_users
  for all using (tenant_id = public.current_tenant_id())
  with check (tenant_id = public.current_tenant_id());

create policy products_isolation on public.products
  for all using (tenant_id = public.current_tenant_id())
  with check (tenant_id = public.current_tenant_id());

create policy error_codes_isolation on public.error_codes
  for all using (tenant_id = public.current_tenant_id())
  with check (tenant_id = public.current_tenant_id());

create policy chat_sessions_isolation on public.chat_sessions
  for all using (tenant_id = public.current_tenant_id())
  with check (tenant_id = public.current_tenant_id());

create policy chat_messages_isolation on public.chat_messages
  for all using (tenant_id = public.current_tenant_id())
  with check (tenant_id = public.current_tenant_id());

create policy orders_isolation on public.orders
  for all using (tenant_id = public.current_tenant_id())
  with check (tenant_id = public.current_tenant_id());

create policy usage_log_isolation on public.usage_log
  for all using (tenant_id = public.current_tenant_id())
  with check (tenant_id = public.current_tenant_id());

-- Note: the Supabase service_role and Postgres superuser bypass RLS.
-- The FastAPI app connects as a regular role and MUST call
--   SELECT set_config('partsai.tenant_id', $1, true);
-- at the start of every request (see apps/api/app/deps.py).

-- ── updated_at trigger ──
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger products_set_updated_at
  before update on public.products
  for each row execute function public.set_updated_at();
