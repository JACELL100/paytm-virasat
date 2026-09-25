-- =============================================================================
-- Paytm Virasat — 0003_demo_seed.sql
--
-- Seeds the demo persona from Implementation_Plan.md section 19
-- ("Demo Script & Seed Data"): Owner Rajesh Patil, 2 nominees, 3 guardians,
-- and 7 assets.
--
-- *** WHY THIS MIGRATION DOES NOT INSERT ANY auth-linked ROWS ***
-- `profiles.id` is a foreign key to `auth.users.id`, and `auth.users` rows
-- only exist once a real person actually signs in via Google OAuth. At
-- migration time (`supabase db push` / `supabase db reset`) no such user
-- exists yet, so this migration CANNOT insert into `profiles`, and it leaves
-- every `owner_id` / `user_id` column NULL on the rows it does create.
--
-- Everything that does NOT depend on an auth user (institution references,
-- the vault's static config, nominee/guardian shells, and the full asset
-- list with realistic values) IS fully seeded here, keyed off a small set of
-- FIXED, WELL-KNOWN UUIDs (see the "Demo entity IDs" block below). The
-- backend's `POST /demo/reset` endpoint is expected to:
--   1. Ensure `auth.users` rows exist for the demo Google accounts (Rajesh,
--      Sunita, Aarav, Suresh, Imran, Dr. Mehta) — created automatically by
--      Supabase Auth the first time each signs in, or provisioned via the
--      Supabase Admin API for a scripted reset.
--   2. Upsert a `profiles` row for each (`id` = that `auth.users.id`).
--   3. UPDATE the rows below, matching on the fixed demo UUIDs (or the
--      `meta->>'demo_persona'` tag on `assets`), to attach:
--        - `vaults.owner_id`      = Rajesh's profile id
--        - `nominees.user_id`     = Sunita's / Aarav's profile id
--        - `guardians.user_id`    = Suresh's / Imran's / Dr. Mehta's profile id
--        - `assets.owner_id`      = Rajesh's profile id
-- This keeps `supabase db reset` / `db push` runnable in CI and on a fresh
-- project with zero real users, while still giving the demo a fully-formed
-- vault, nominee shares, guardian threshold, and asset list to render.
--
-- Idempotency: every insert below is keyed on a fixed UUID or a natural
-- unique key and guarded with `on conflict ... do nothing`, so re-running
-- this migration in local dev (`supabase db reset`) is safe.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Demo entity IDs (fixed, well-known — mirror these constants in backend
-- code, e.g. `backend/app/demo_constants.py`, so `/demo/reset` can find and
-- re-link these exact rows once real auth users exist).
-- -----------------------------------------------------------------------------
-- vault:                00000000-0000-0000-0000-000000000001
-- nominee  Sunita Patil: 00000000-0000-0000-0000-000000000011  (wife, 60%)
-- nominee  Aarav Patil:  00000000-0000-0000-0000-000000000012  (son, 40%)
-- guardian Suresh Patil: 00000000-0000-0000-0000-000000000021  (brother)
-- guardian Imran Shaikh: 00000000-0000-0000-0000-000000000022  (friend)
-- guardian Dr. Mehta:    00000000-0000-0000-0000-000000000023  (family doctor)
-- asset LIC endowment:        00000000-0000-0000-0000-000000000031
-- asset HDFC Life term:       00000000-0000-0000-0000-000000000032  (nominee missing)
-- asset SBI FD:                00000000-0000-0000-0000-000000000033
-- asset Axis MF SIP:           00000000-0000-0000-0000-000000000034
-- asset Paytm Money stocks:    00000000-0000-0000-0000-000000000035
-- asset Star Health floater:   00000000-0000-0000-0000-000000000036
-- asset Bajaj Finance loan:    00000000-0000-0000-0000-000000000037
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- Vault (owner_id NULL — attached to Rajesh's profile by /demo/reset)
-- -----------------------------------------------------------------------------
insert into vaults (
  id, owner_id, chain_vault_id, state, inactivity_secs, challenge_secs,
  threshold, epoch, manifest_hash, manifest_path
)
values (
  '00000000-0000-0000-0000-000000000001', -- demo vault
  null,                                    -- attached later: Rajesh Patil's profile id
  null,                                    -- assigned once created on-chain
  'draft',
  15552000, -- ~180 days
  604800,   -- ~7 days
  2,        -- 2 of 3 guardians required to attest
  0,
  null,
  null
)
on conflict (id) do nothing;

-- -----------------------------------------------------------------------------
-- Nominees (user_id NULL — attached to Sunita's / Aarav's profile by /demo/reset)
-- -----------------------------------------------------------------------------
insert into nominees (id, vault_id, name, relation, email, phone, share_bps, user_id, invite_status)
values
  (
    '00000000-0000-0000-0000-000000000011',
    '00000000-0000-0000-0000-000000000001',
    'Sunita Patil', 'wife', 'sunita.patil.demo@example.com', '+91-9800000011',
    6000, null, 'accepted'
  ),
  (
    '00000000-0000-0000-0000-000000000012',
    '00000000-0000-0000-0000-000000000001',
    'Aarav Patil', 'son', 'aarav.patil.demo@example.com', '+91-9800000012',
    4000, null, 'accepted'
  )
on conflict (id) do nothing;

-- -----------------------------------------------------------------------------
-- Guardians (user_id NULL — attached by /demo/reset; 2 of 3 required to attest,
-- per vaults.threshold above). Demo script treats invites as already accepted
-- so the live demo can skip the invite-and-wait flow.
-- -----------------------------------------------------------------------------
insert into guardians (id, vault_id, name, relation, email, user_id, status, onchain_added)
values
  (
    '00000000-0000-0000-0000-000000000021',
    '00000000-0000-0000-0000-000000000001',
    'Suresh Patil', 'brother', 'suresh.patil.demo@example.com', null, 'accepted', false
  ),
  (
    '00000000-0000-0000-0000-000000000022',
    '00000000-0000-0000-0000-000000000001',
    'Imran Shaikh', 'friend', 'imran.shaikh.demo@example.com', null, 'accepted', false
  ),
  (
    '00000000-0000-0000-0000-000000000023',
    '00000000-0000-0000-0000-000000000001',
    'Dr. Mehta', 'family doctor', 'dr.mehta.demo@example.com', null, 'accepted', false
  )
on conflict (id) do nothing;

-- -----------------------------------------------------------------------------
-- Assets (owner_id NULL — attached to Rajesh's profile by /demo/reset).
-- Each row is tagged `meta->>'demo_persona' = 'rajesh_patil'` as a
-- belt-and-suspenders lookup key in addition to the fixed id.
-- institution_id is resolved from the slugs seeded in 0002_institutions_seed.sql.
-- -----------------------------------------------------------------------------
insert into assets (
  id, owner_id, type, institution_id, label, account_ref_masked, account_ref_enc,
  value_estimate, premium_amount, frequency, nominee_status, nominee_names,
  source, confidence, meta
)
values
  (
    '00000000-0000-0000-0000-000000000031',
    null,
    'life_endowment',
    (select id from institutions where slug = 'lic'),
    'LIC Endowment Plan',
    'XXXXXXXX1201', null,
    1000000, 12500, 'yearly',
    'ok', array['Sunita Patil','Aarav Patil'],
    'demo_seed', 1.0,
    '{"demo_persona":"rajesh_patil","policy_type":"endowment","maturity_year":2034}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000032',
    null,
    'term_life',
    (select id from institutions where slug = 'hdfc-life'),
    'HDFC Life Term Plan',
    'XXXXXXXX5602', null,
    5000000, 18000, 'yearly',
    'missing', '{}',
    'demo_seed', 1.0,
    '{"demo_persona":"rajesh_patil","policy_type":"term","term_years":30,"urgent":true,"note":"No nominee registered - fix before sealing vault"}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000033',
    null,
    'fd',
    (select id from institutions where slug = 'sbi-bank'),
    'SBI Fixed Deposit',
    'XXXXXXXX7788', null,
    300000, null, 'one_time',
    'ok', array['Sunita Patil','Aarav Patil'],
    'demo_seed', 1.0,
    '{"demo_persona":"rajesh_patil","interest_rate_pct":6.75,"maturity_date":"2027-03-15"}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000034',
    null,
    'mutual_fund',
    (select id from institutions where slug = 'axis-bank'),
    'Axis Bluechip Fund SIP',
    'XXXXXXXX4521', null,
    null, 8000, 'monthly',
    'ok', array['Sunita Patil'],
    'demo_seed', 1.0,
    '{"demo_persona":"rajesh_patil","scheme_name":"Axis Bluechip Fund - Growth","sip_day":5}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000035',
    null,
    'stocks',
    (select id from institutions where slug = 'paytm-money'),
    'Paytm Money Stock Portfolio',
    'XXXXXXXX9981', null,
    250000, null, null,
    'ok', array['Sunita Patil','Aarav Patil'],
    'demo_seed', 1.0,
    '{"demo_persona":"rajesh_patil","broker":"Paytm Money","holdings_count":12}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000036',
    null,
    'health',
    (select id from institutions where slug = 'star-health'),
    'Star Health Family Floater',
    'XXXXXXXX3345', null,
    1000000, 22000, 'yearly',
    'ok', array['Sunita Patil','Aarav Patil'],
    'demo_seed', 1.0,
    '{"demo_persona":"rajesh_patil","policy_type":"family_floater","sum_insured":1000000,"members_covered":4}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000037',
    null,
    'loan',
    (select id from institutions where slug = 'bajaj-finance'),
    'Bajaj Finance Business Loan',
    'XXXXXXXX6610', null,
    1500000, null, 'monthly',
    'ok', array['Sunita Patil'],
    'demo_seed', 1.0,
    '{"demo_persona":"rajesh_patil","loan_type":"business_loan","outstanding_amount":1500000,"has_loan_protection_cover":true,"urgent":true,"note":"Loan protection claim should be filed first so EMIs stop"}'::jsonb
  )
on conflict (id) do nothing;
