# Paytm Virasat

AI-powered legacy vault and claims co-pilot for Track 2 (AI-Powered Financial Journeys) — Paytm Build for India AI Hackathon, Mumbai Edition.

See [`Implementation_Plan.md`](Implementation_Plan.md) for the full architecture, schema, contract design and timeline.

## Structure

- `frontend/` — Next.js (App Router, TypeScript, Tailwind) — deploys to Vercel
- `backend/` — FastAPI (Python 3.11) — deploys to Render
- `contracts/` — Solidity contracts, compiled and deployed via `web3.py` to Sepolia
- `supabase/` — Postgres migrations + seed data

## Quick start

See each folder's own README for setup. Copy `.env.example` → `.env` (`backend/`) or `.env.local` (`frontend/`) and fill in keys before running.
