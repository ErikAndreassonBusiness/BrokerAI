-- User-entered data for BrokerAI (issue #56, ADR 0005). Structure only: no data, no secrets.
-- Apply by pasting into the Supabase SQL editor. Never edit this file once applied; add a new migration.

create table public.valuations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  ticker text not null,
  value numeric not null,
  valued_on date not null default current_date,
  note text not null default '',
  created_at timestamptz default now()
);

create table public.customers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  ticker text not null,
  name text not null,
  url text check (url is null or url ~ '^https?://'),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create unique index customers_user_ticker_name on public.customers (user_id, ticker, lower(name));

create table public.notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  ticker text not null,
  body text not null default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (user_id, ticker)
);

create function public.set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
create trigger customers_set_updated_at before update on public.customers
  for each row execute function public.set_updated_at();
create trigger notes_set_updated_at before update on public.notes
  for each row execute function public.set_updated_at();

alter table public.valuations enable row level security;
alter table public.customers enable row level security;
alter table public.notes enable row level security;

-- valuations is append-only: select and insert only
create policy valuations_select on public.valuations for select to authenticated
  using (auth.uid() = user_id);
create policy valuations_insert on public.valuations for insert to authenticated
  with check (auth.uid() = user_id);

create policy customers_select on public.customers for select to authenticated
  using (auth.uid() = user_id);
create policy customers_insert on public.customers for insert to authenticated
  with check (auth.uid() = user_id);
create policy customers_update on public.customers for update to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy customers_delete on public.customers for delete to authenticated
  using (auth.uid() = user_id);

create policy notes_select on public.notes for select to authenticated
  using (auth.uid() = user_id);
create policy notes_insert on public.notes for insert to authenticated
  with check (auth.uid() = user_id);
create policy notes_update on public.notes for update to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy notes_delete on public.notes for delete to authenticated
  using (auth.uid() = user_id);
