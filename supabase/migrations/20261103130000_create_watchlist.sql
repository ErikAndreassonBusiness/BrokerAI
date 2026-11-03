-- Per-user watchlist for BrokerAI (issue #79). Structure only: no data, no secrets.
-- Apply by pasting into the Supabase SQL editor. Never edit this file once applied; add a new migration.

create table public.watchlist (
  user_id uuid not null default auth.uid(),
  ticker text not null check (ticker ~ '^[A-Za-z0-9.-]{1,20}$'),
  created_at timestamptz not null default now(),
  primary key (user_id, ticker)
);

alter table public.watchlist enable row level security;

-- watchlist rows are added and removed, never updated: select, insert and delete only
create policy watchlist_select on public.watchlist for select to authenticated
  using (auth.uid() = user_id);
create policy watchlist_insert on public.watchlist for insert to authenticated
  with check (auth.uid() = user_id);
create policy watchlist_delete on public.watchlist for delete to authenticated
  using (auth.uid() = user_id);
