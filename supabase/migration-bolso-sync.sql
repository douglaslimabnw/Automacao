-- Bolso em Dia — tabela da "Família sincronizada" (projeto Supabase "appfinanceiro")
-- Uma linha por família: o estado inteiro do app fica em `payload` (JSON).
-- Segurança: a linha só pode ser lida/escrita por quem apresenta a chave-secreta
-- da família no cabeçalho HTTP "x-Bolso-key" (confere nas políticas RLS abaixo).
-- Sem a chave, nem listando a tabela se enxerga qualquer coisa. Sem DELETE.
create table if not exists public.Bolso_sync (
  household_key text primary key check (length(household_key) between 20 and 200),
  payload       jsonb not null default '{}'::jsonb,
  versao        bigint not null default 1,
  atualizado_por text,
  updated_at    timestamptz not null default now()
);

alter table public.Bolso_sync enable row level security;
grant select, insert, update on public.Bolso_sync to anon;

drop policy if exists Bolso_select on public.Bolso_sync;
drop policy if exists Bolso_insert on public.Bolso_sync;
drop policy if exists Bolso_update on public.Bolso_sync;

create policy Bolso_select on public.Bolso_sync
  for select to anon
  using (household_key = (nullif(current_setting('request.headers', true), '')::json ->> 'x-Bolso-key'));

create policy Bolso_insert on public.Bolso_sync
  for insert to anon
  with check (household_key = (nullif(current_setting('request.headers', true), '')::json ->> 'x-Bolso-key'));

create policy Bolso_update on public.Bolso_sync
  for update to anon
  using (household_key = (nullif(current_setting('request.headers', true), '')::json ->> 'x-Bolso-key'))
  with check (household_key = (nullif(current_setting('request.headers', true), '')::json ->> 'x-Bolso-key'));
