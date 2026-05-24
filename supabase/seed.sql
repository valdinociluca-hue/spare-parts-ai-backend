-- Pre-seed the two Phase 1 tenants.
-- Re-runnable: uses ON CONFLICT DO NOTHING on slug.

insert into public.tenants (slug, name, region, llm_provider, brand_color, language, widget_api_key, plan)
values
  ('lvtrade',  'LV Trade', 'RU',     'yandex', '#1565C0', 'ru', 'pk_live_lvtrade_'  || encode(gen_random_bytes(16), 'hex'), 'pro'),
  ('equipart', 'Equipart', 'GLOBAL', 'claude', '#2E7D32', 'en', 'pk_live_equipart_' || encode(gen_random_bytes(16), 'hex'), 'pro')
on conflict (slug) do nothing;
