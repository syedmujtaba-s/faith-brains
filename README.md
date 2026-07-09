# FaithBrains

Standalone Islamic learning assistant — Quran search, Hadith search, AI explanations grounded in
retrieved sources with visible references, and a strict no-fatwa safety guard.

> FaithBrains is an educational tool. It is **not** a religious authority, does not issue fatwas or
> rulings, and is not a replacement for qualified scholars.

## Architecture

- **Backend** (`backend/`): Python 3.12+ / FastAPI, async SQLAlchemy 2.0, PostgreSQL 17 + pgvector,
  Alembic, uv. Hybrid retrieval (vector + full-text, Reciprocal Rank Fusion) over Quran + Hadith.
- **AI** (`app/ai/`): pluggable provider (`AI_PROVIDER=openai|anthropic|auto`) generates grounded
  answers with `[n]` citations, strictly limited to retrieved sources; a small classifier model
  routes every question first (educational / fatwa-seeking / crisis / out-of-scope). Fatwa-seeking
  questions get educational context plus an explicit no-ruling referral; crisis questions get a
  deterministic supportive response with no model generation. Defaults: OpenAI gpt-5-mini answers +
  gpt-5-nano classifier when `OPENAI_API_KEY` is set; Claude Sonnet 5 + Haiku 4.5 on
  `ANTHROPIC_API_KEY`. Voyage voyage-4 embeddings power the semantic search signal.
- **Frontend** (`frontend/`): Next.js 15 (React + TypeScript) + Tailwind 4. Tabs: Ask / Quran /
  Hadith / Learn / Saved (device-local bookmarks). Proxies `/api/v1/*` to the backend, so no CORS.

## Quickstart (frontend)

```powershell
cd frontend
npm install
npm run dev          # backend assumed at http://localhost:8000
# custom backend port:  $env:BACKEND_URL="http://localhost:8010"; npm run dev
# -> http://localhost:3000
```

## Quickstart (backend)

```powershell
# 1. Database (Docker) — or point DATABASE_URL at any Postgres 17 with pgvector
docker compose up -d db

# 2. Configure
copy .env.example .env    # then fill in keys

# 3. Install + migrate
cd backend
uv sync
uv run alembic upgrade head

# 4. Download + ingest source corpora (Quran, translations, Hadith)
uv run python scripts/download_sources.py
uv run python -m app.ingest.quran_tanzil
uv run python -m app.ingest.quran_metadata
uv run python -m app.ingest.translations_quranenc
uv run python -m app.ingest.hadith_fawazahmed
uv run python -m app.ingest.validate     # must print ALL CHECKS PASS

# 5. Embeddings (requires VOYAGE_API_KEY in .env; resumable)
uv run python -m app.ingest.embed

# 6. Run
uv run uvicorn app.main:app --reload
# -> http://localhost:8000/docs
```

## AI answers (`POST /api/v1/ask`)

Requires `ANTHROPIC_API_KEY` in `.env` (returns 503 with a clear message otherwise).

```powershell
curl -X POST http://localhost:8000/api/v1/ask `
  -H "Content-Type: application/json" `
  -d '{"question": "What does the Quran teach about patience?"}'
# -> { category, answer (with [n] citations), sources[n], disclaimer }
```

## Admin & hardening (Milestone 4)

- Every `/ask` is logged to `ask_logs` (question, category, answer, source refs, provider/model,
  latency, errors) for quality review.
- `GET /api/v1/admin/stats` and `GET /api/v1/admin/asks` require the `X-Admin-Token` header
  matching `ADMIN_TOKEN` in `.env`; admin is disabled while the token is unset/default.
  Frontend dashboard: `http://localhost:3000/admin`.
- Rate limits (per IP, in-memory): `/ask` 15/min, `/search` 60/min — swap for Redis when scaling out.
- Security headers on all responses (nosniff, frame-deny, referrer policy).

## Tests

```powershell
cd backend
uv run pytest            # unit tests (no DB needed) + integration tests (need running db)
```

## Data sources & licensing

See [docs/licensing.md](docs/licensing.md). Summary: Quran Arabic text from the Tanzil Project
(verbatim, attributed), English translations from QuranEnc.com (verbatim, versioned, attributed),
Hadith corpus from the fawazahmed0/hadith-api open dataset. Attribution is a license obligation and
is displayed in the app.
