-- ─────────────────────────────────────────────────────────────
-- PartsAI Y3-Y4 marketplace-ready fields
-- Adds the columns the cross-tenant marketplace needs to function
-- (tenant locale, currency, vertical; products' canonical part
-- identity; anonymous search continuity across tenant boundaries).
-- ─────────────────────────────────────────────────────────────

alter table public.products
  add column if not exists manufacturer_part_number text,
  add column if not exists manufacturer            text;

create index if not exists idx_products_mpn
  on public.products(tenant_id, manufacturer_part_number)
  where manufacturer_part_number is not null;

alter table public.tenants
  add column if not exists country  text,
  add column if not exists city     text,
  add column if not exists timezone text,
  add column if not exists currency text not null default 'EUR',
  add column if not exists vertical text not null default 'horeca';

alter table public.chat_sessions
  add column if not exists anonymous_search_id text;

create index if not exists idx_chat_sessions_anon_search
  on public.chat_sessions(anonymous_search_id)
  where anonymous_search_id is not null;
