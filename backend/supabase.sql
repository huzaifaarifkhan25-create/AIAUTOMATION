-- Run once in your Supabase SQL editor. The backend uses the service role key.
create table if not exists public.backend_records (
    kind text not null check (kind in ('businesses','analyses','workflows','contacts','calls','discovery_jobs')),
    id text not null,
    payload jsonb not null,
    primary key (kind, id)
);
-- Also upgrades an existing table created by the first milestone.
alter table public.backend_records drop constraint if exists backend_records_kind_check;
alter table public.backend_records add constraint backend_records_kind_check
    check (kind in ('businesses','analyses','workflows','contacts','calls','discovery_jobs'));
alter table public.backend_records enable row level security;
revoke all on public.backend_records from anon, authenticated;
grant select, insert, update, delete on public.backend_records to service_role;
