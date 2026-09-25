-- =============================================================================
-- Paytm Virasat — 0001_init.sql
-- Core schema: enums, tables, indexes, RLS, updated_at trigger, storage buckets.
--
-- RLS POLICY (documented per Implementation_Plan.md section 9):
--   Every table has Row Level Security ENABLED with NO permissive policies
--   defined for `anon` or `authenticated` roles. This means those roles are
--   denied all access by default (Postgres RLS defaults to deny when RLS is
--   enabled and no policy matches). The backend (FastAPI) talks to Supabase
--   exclusively via the SERVICE ROLE key, which bypasses RLS entirely, so no
--   explicit `USING (false)` policies are required for the deny-by-default
--   behaviour to hold. We enable RLS on every table for defense-in-depth
--   (so that if anon/authenticated keys ever leak into the frontend, no rows
--   are readable/writable) and do not add any policies in this migration.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Extensions
-- -----------------------------------------------------------------------------
create extension if not exists pgcrypto;   -- gen_random_uuid()
create extension if not exists pg_trgm;    -- helpful for fuzzy alias search later

-- -----------------------------------------------------------------------------
-- Enums
-- -----------------------------------------------------------------------------
create type asset_type as enum ('term_life','life_endowment','ulip','health','motor','fd','savings',
  'mutual_fund','stocks','ppf','epf','nps','gold','loan','credit_card','other');
create type nominee_status as enum ('ok','missing','outdated','unknown');
create type vault_state as enum ('draft','active','challenge','released','revoked');
create type claim_status as enum ('not_started','docs_pending','ready_to_file','filed',
  'under_review','query_raised','settled','rejected','escalated');
create type tx_status as enum ('queued','sent','mined','failed');

-- -----------------------------------------------------------------------------
-- Reusable updated_at trigger function
-- -----------------------------------------------------------------------------
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- -----------------------------------------------------------------------------
-- profiles  (id = auth.users.id)
-- -----------------------------------------------------------------------------
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  email text,
  phone text,
  language text default 'en',
  annual_income numeric,
  wallet_address text,
  wallet_key_enc text,
  roles text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger trg_profiles_updated_at
  before update on profiles
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- consents
-- -----------------------------------------------------------------------------
create table consents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  purpose text not null,
  version text not null,
  granted_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_consents_user_id on consents(user_id);

create trigger trg_consents_updated_at
  before update on consents
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- institutions
-- -----------------------------------------------------------------------------
create table institutions (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  kind text not null, -- life_insurer / health_insurer / bank / mf_registrar / epfo / nps / lender / broker / other
  aliases text[] not null default '{}',
  claim_email text,
  grievance_email text,
  portal_url text,
  sla_days integer,
  required_docs jsonb not null default '[]'::jsonb,
  source_url text,
  last_verified date,
  search tsvector,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_institutions_search on institutions using gin(search);
create index idx_institutions_aliases on institutions using gin(aliases);

create trigger trg_institutions_updated_at
  before update on institutions
  for each row execute function set_updated_at();

create or replace function institutions_search_update()
returns trigger
language plpgsql
as $$
begin
  new.search :=
    setweight(to_tsvector('simple', coalesce(new.name, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(array_to_string(new.aliases, ' '), '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(new.kind, '')), 'C');
  return new;
end;
$$;

create trigger trg_institutions_search
  before insert or update on institutions
  for each row execute function institutions_search_update();

-- -----------------------------------------------------------------------------
-- assets
-- -----------------------------------------------------------------------------
create table assets (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references profiles(id) on delete cascade,
  type asset_type not null,
  institution_id uuid references institutions(id),
  label text not null,
  account_ref_masked text,
  account_ref_enc text,
  value_estimate numeric,
  premium_amount numeric,
  frequency text, -- monthly / quarterly / yearly / one_time / sip
  nominee_status nominee_status not null default 'unknown',
  nominee_names text[] not null default '{}',
  source text, -- statement_upload / paytm_feed / manual / discovery
  confidence numeric,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_assets_owner_id on assets(owner_id);
create index idx_assets_institution_id on assets(institution_id);
create index idx_assets_type on assets(type);

create trigger trg_assets_updated_at
  before update on assets
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- discovery_suggestions
-- -----------------------------------------------------------------------------
create table discovery_suggestions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references profiles(id) on delete cascade,
  source text not null, -- statement_upload / paytm_feed / sms_parse / manual
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending', -- pending / accepted / rejected
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_discovery_suggestions_owner_id on discovery_suggestions(owner_id);
create index idx_discovery_suggestions_status on discovery_suggestions(status);

create trigger trg_discovery_suggestions_updated_at
  before update on discovery_suggestions
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- documents
-- -----------------------------------------------------------------------------
create table documents (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references profiles(id) on delete cascade,
  asset_id uuid references assets(id) on delete set null,
  kind text not null, -- policy / statement / death_certificate / id_proof / other
  storage_path text not null,
  sha256 text,
  extracted jsonb not null default '{}'::jsonb,
  status text not null default 'uploaded',
  chunks jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_documents_owner_id on documents(owner_id);
create index idx_documents_asset_id on documents(asset_id);
create unique index idx_documents_sha256 on documents(sha256) where sha256 is not null;

create trigger trg_documents_updated_at
  before update on documents
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- vaults
-- -----------------------------------------------------------------------------
create table vaults (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references profiles(id) on delete cascade,
  chain_vault_id bigint,
  state vault_state not null default 'draft',
  inactivity_secs bigint not null default 15552000, -- ~180 days default
  challenge_secs bigint not null default 604800,     -- ~7 days default
  threshold integer not null default 2,               -- guardians required to attest
  epoch integer not null default 0,
  manifest_hash text,
  manifest_path text,
  escrow_share_enc text,
  recovery_share_enc text,
  challenge_ends_at timestamptz,
  last_activity_at timestamptz,
  last_heartbeat_onchain_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_vaults_owner_id on vaults(owner_id);
create unique index idx_vaults_chain_vault_id on vaults(chain_vault_id) where chain_vault_id is not null;
create index idx_vaults_state on vaults(state);

create trigger trg_vaults_updated_at
  before update on vaults
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- nominees
-- -----------------------------------------------------------------------------
create table nominees (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid not null references vaults(id) on delete cascade,
  name text not null,
  relation text,
  email text,
  phone text,
  share_bps integer not null, -- basis points, 10000 = 100%
  user_id uuid references profiles(id) on delete set null,
  wallet_address text,
  invite_token_hash text,
  invite_status text not null default 'pending', -- pending / sent / accepted / expired
  legacy_key_issued_at timestamptz,
  credential_token_id bigint,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_nominees_share_bps check (share_bps >= 0 and share_bps <= 10000)
);

create index idx_nominees_vault_id on nominees(vault_id);
create index idx_nominees_user_id on nominees(user_id);

create trigger trg_nominees_updated_at
  before update on nominees
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- guardians
-- -----------------------------------------------------------------------------
create table guardians (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid not null references vaults(id) on delete cascade,
  name text not null,
  relation text,
  email text,
  user_id uuid references profiles(id) on delete set null,
  wallet_address text,
  invite_token_hash text,
  status text not null default 'pending', -- pending / invited / accepted / declined
  onchain_added boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_guardians_vault_id on guardians(vault_id);
create index idx_guardians_user_id on guardians(user_id);

create trigger trg_guardians_updated_at
  before update on guardians
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- activity_events
-- -----------------------------------------------------------------------------
create table activity_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  kind text not null, -- login / payment / heartbeat / onchain_heartbeat / etc
  occurred_at timestamptz not null default now(),
  source text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_activity_events_user_occurred on activity_events(user_id, occurred_at desc);

create trigger trg_activity_events_updated_at
  before update on activity_events
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- attestations
-- -----------------------------------------------------------------------------
create table attestations (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid not null references vaults(id) on delete cascade,
  guardian_id uuid references guardians(id) on delete set null,
  document_id uuid references documents(id) on delete set null,
  death_cert_hash text,
  extracted jsonb not null default '{}'::jsonb,
  name_match_score numeric,
  signature text,
  tx_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_attestations_vault_id on attestations(vault_id);
create index idx_attestations_guardian_id on attestations(guardian_id);

create trigger trg_attestations_updated_at
  before update on attestations
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- chain_txs
-- -----------------------------------------------------------------------------
create table chain_txs (
  id uuid primary key default gen_random_uuid(),
  idempotency_key text not null,
  kind text not null, -- e.g. create_vault / heartbeat / start_challenge / attest / release / mint_credential
  vault_id uuid references vaults(id) on delete set null,
  payload jsonb not null default '{}'::jsonb,
  tx_hash text,
  nonce bigint,
  status tx_status not null default 'queued',
  gas_used bigint,
  error text,
  attempts integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index idx_chain_txs_idempotency_key on chain_txs(idempotency_key);
create index idx_chain_txs_vault_id on chain_txs(vault_id);
create index idx_chain_txs_status on chain_txs(status);

create trigger trg_chain_txs_updated_at
  before update on chain_txs
  for each row execute function set_updated_at();

-- (attestations.tx_id references chain_txs, added after chain_txs exists)
alter table attestations
  add constraint fk_attestations_tx_id foreign key (tx_id) references chain_txs(id) on delete set null;

-- -----------------------------------------------------------------------------
-- chain_events
-- -----------------------------------------------------------------------------
create table chain_events (
  id uuid primary key default gen_random_uuid(),
  block_number bigint not null,
  tx_hash text not null,
  log_index integer not null,
  contract text not null,
  event text not null,
  args jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index idx_chain_events_tx_hash_log_index on chain_events(tx_hash, log_index);
create index idx_chain_events_contract_event on chain_events(contract, event);
create index idx_chain_events_block_number on chain_events(block_number);

create trigger trg_chain_events_updated_at
  before update on chain_events
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- sync_cursors
-- -----------------------------------------------------------------------------
create table sync_cursors (
  id uuid primary key default gen_random_uuid(),
  contract text not null unique,
  last_block bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger trg_sync_cursors_updated_at
  before update on sync_cursors
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- claims
-- -----------------------------------------------------------------------------
create table claims (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid references vaults(id) on delete cascade,
  nominee_id uuid references nominees(id) on delete set null,
  asset_id uuid references assets(id) on delete set null,
  institution_id uuid references institutions(id),
  status claim_status not null default 'not_started',
  priority_score numeric,
  checklist jsonb not null default '[]'::jsonb,
  pack_path text,
  filed_at timestamptz,
  sla_due_at timestamptz,
  claim_ref text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_claims_vault_id on claims(vault_id);
create index idx_claims_nominee_id on claims(nominee_id);
create index idx_claims_asset_id on claims(asset_id);
create index idx_claims_institution_id on claims(institution_id);
create index idx_claims_status on claims(status);

create trigger trg_claims_updated_at
  before update on claims
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- claim_events
-- -----------------------------------------------------------------------------
create table claim_events (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references claims(id) on delete cascade,
  status claim_status,
  note text,
  doc_hash text,
  tx_id uuid references chain_txs(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_claim_events_claim_id on claim_events(claim_id);

create trigger trg_claim_events_updated_at
  before update on claim_events
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- copilot_sessions / copilot_messages
-- -----------------------------------------------------------------------------
create table copilot_sessions (
  id uuid primary key default gen_random_uuid(),
  vault_id uuid references vaults(id) on delete cascade,
  user_id uuid references profiles(id) on delete cascade,
  language text default 'en',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_copilot_sessions_vault_id on copilot_sessions(vault_id);
create index idx_copilot_sessions_user_id on copilot_sessions(user_id);

create trigger trg_copilot_sessions_updated_at
  before update on copilot_sessions
  for each row execute function set_updated_at();

create table copilot_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references copilot_sessions(id) on delete cascade,
  role text not null, -- user / assistant / tool / system
  content text,
  tool_calls jsonb not null default '[]'::jsonb,
  audio_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_copilot_messages_session_id on copilot_messages(session_id);

create trigger trg_copilot_messages_updated_at
  before update on copilot_messages
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- notifications
-- -----------------------------------------------------------------------------
create table notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  kind text not null,
  payload jsonb not null default '{}'::jsonb,
  sent_at timestamptz,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_notifications_user_id on notifications(user_id);
create index idx_notifications_sent_at on notifications(sent_at);

create trigger trg_notifications_updated_at
  before update on notifications
  for each row execute function set_updated_at();

-- -----------------------------------------------------------------------------
-- Row Level Security: enable on every table, no policies (deny-by-default).
-- Service role bypasses RLS; anon/authenticated get zero access.
-- -----------------------------------------------------------------------------
alter table profiles enable row level security;
alter table consents enable row level security;
alter table institutions enable row level security;
alter table assets enable row level security;
alter table discovery_suggestions enable row level security;
alter table documents enable row level security;
alter table vaults enable row level security;
alter table nominees enable row level security;
alter table guardians enable row level security;
alter table activity_events enable row level security;
alter table attestations enable row level security;
alter table chain_txs enable row level security;
alter table chain_events enable row level security;
alter table sync_cursors enable row level security;
alter table claims enable row level security;
alter table claim_events enable row level security;
alter table copilot_sessions enable row level security;
alter table copilot_messages enable row level security;
alter table notifications enable row level security;

-- -----------------------------------------------------------------------------
-- Storage buckets (all private; backend issues signed URLs valid <= 10 minutes)
-- -----------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values
  ('documents', 'documents', false),
  ('death-certificates', 'death-certificates', false),
  ('sealed-manifests', 'sealed-manifests', false),
  ('claim-packs', 'claim-packs', false),
  ('voice-notes', 'voice-notes', false)
on conflict (id) do nothing;
