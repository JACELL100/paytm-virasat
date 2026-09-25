# Paytm Virasat — Supabase

This folder is the Supabase project for Paytm Virasat: schema, institutions
knowledge base, demo seed data, storage buckets, and local dev config. See
`Implementation_Plan.md` section 9 (schema), 12.6 (institutions), 15.1
(deployment), and 19 (demo persona) for the full spec these files implement.

## Contents

- `migrations/0001_init.sql` — enums, all tables, indexes, RLS (enabled,
  deny-by-default, no policies — see the comment at the top of the file),
  the shared `updated_at` trigger, and the 5 private storage buckets
  (`documents`, `death-certificates`, `sealed-manifests`, `claim-packs`,
  `voice-notes`). **Storage buckets are created here, in SQL, not by hand in
  the dashboard.**
- `migrations/0002_institutions_seed.sql` — ~20 real Indian institutions
  (life/health insurers, banks, MF registrars, EPFO, NPS, a lender, Paytm
  Money/Insurance) with aliases, claim/grievance contacts, portal URLs, SLA
  days, and `required_docs`. **Re-verify these against official sources
  before the live demo** — see the warning at the top of that file.
- `migrations/0003_demo_seed.sql` — the demo persona (Rajesh Patil, 2
  nominees, 3 guardians, 7 assets) from section 19. Rows that need a real
  `auth.users` row (`profiles`, and every `owner_id`/`user_id` column) are
  left `NULL` here; the backend's `POST /demo/reset` endpoint attaches them
  once the demo Google accounts actually sign in. See the comment block at
  the top of that file for the exact fixed UUIDs it uses and the linkage
  contract the backend must follow.
- `seed.sql` — thin top-level pointer file (standard Supabase CLI
  convention: run automatically by `supabase db reset`). The real seed data
  lives in the numbered migrations above so it also applies via
  `supabase db push` against a real project.
- `config.toml` — minimal local Supabase CLI config (`supabase start`).

## Install the Supabase CLI

Pick one:

```powershell
# Scoop (Windows)
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# or npm, as a dev dependency of the repo (no global install)
npm install --save-dev supabase

# or npx, no install at all
npx supabase --version
```

See https://supabase.com/docs/guides/cli/getting-started for other package
managers (Homebrew, Chocolatey, direct binary download for Windows).

## Local development

From this `supabase/` folder:

```powershell
supabase start        # boots the local Docker stack (Postgres, Studio, Auth, Storage, Inbucket...)
supabase db reset      # drops the local db, re-applies migrations/*.sql in order, then runs seed.sql
```

`supabase start` requires Docker Desktop running. Once it's up, Studio is at
`http://localhost:54323`, the API at `http://localhost:54321`, and Postgres
at `localhost:54322` (see `config.toml` for the exact ports). `supabase db
reset` is the fast inner loop while iterating on migrations — it is
idempotent-safe here because `0002` and `0003` use `on conflict ... do
nothing`.

To just apply new/changed migration files to an already-running local stack
without a full reset:

```powershell
supabase db push --local
```

## Linking to a real project and deploying migrations

1. Create a project in the Supabase dashboard (region **ap-south-1 /
   Mumbai**, per Implementation_Plan.md section 15.1).
2. From this folder:

   ```powershell
   supabase login
   supabase link --project-ref <project-ref>
   ```

3. Push the schema, institutions, and demo seed:

   ```powershell
   supabase db push
   ```

   This applies `migrations/0001_init.sql`, `0002_institutions_seed.sql`,
   and `0003_demo_seed.sql` in order. It does **not** run the top-level
   `seed.sql` (that only runs locally via `db reset`/`db start`) — which is
   fine, since the real seed data already lives in the migrations.

4. Confirm the 5 storage buckets exist (Storage tab in the dashboard, or
   `select id, public from storage.buckets;` in the SQL editor) — they're
   created by `0001_init.sql`, so this is just a sanity check, not a manual
   step.

## Google OAuth — manual dashboard step (cannot be done via SQL)

Per Implementation_Plan.md section 15.1, the Google Auth provider must be
configured by hand in the Supabase dashboard; there is no migration for
this:

1. In Google Cloud Console, create an OAuth Client ID (Web application).
2. Add the authorized redirect URI:
   `https://<project-ref>.supabase.co/auth/v1/callback`.
3. In the Supabase dashboard: **Authentication → Providers → Google**,
   paste the Client ID and Client Secret, and enable the provider.
4. In **Authentication → URL Configuration**, set Site URL to
   `https://<app>.vercel.app` and add redirect URLs for
   `http://localhost:3000/auth/callback` and
   `https://<app>.vercel.app/auth/callback`.

`config.toml` has a disabled `[auth.external.google]` block for local dev
only (reads `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` from the
environment if you choose to enable it); it has no effect on the hosted
project.

## Notes on the demo seed and `/demo/reset`

`0003_demo_seed.sql` seeds the vault, nominees, guardians, and full asset
list using fixed, well-known UUIDs (documented at the top of that file) so
the migration can run before any real user exists. The backend is
responsible for:

1. Ensuring `auth.users` rows exist for the demo Google accounts.
2. Upserting matching `profiles` rows.
3. Updating `vaults.owner_id`, `nominees.user_id`, `guardians.user_id`, and
   `assets.owner_id` (matched by the fixed demo UUIDs, or by
   `assets.meta->>'demo_persona' = 'rajesh_patil'`) to point at those
   profiles.

This keeps `supabase db reset`/`db push` runnable with zero real users while
still giving `/demo/reset` a fully-formed vault and asset list to attach to
whichever Google accounts are used for the live demo.
