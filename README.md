# Paratus AFSC Roster

Upload an Air Force roster workbook, search members by AFSC, check team feasibility, and ask read-only questions about the active roster.

## Prerequisites

- Python 3.11+
- Node.js 20+

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python server.py
```

API: http://127.0.0.1:8000

Optional: set `OPENAI_API_KEY` in `backend/.env` to enable the Ask chat panel.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Deploy on Railway

Create one Railway project from this GitHub repo, then add three services:

1. **Postgres** — Railway plugin (provides `DATABASE_URL`)
2. **API** — root directory `backend`
3. **Frontend** — root directory `frontend`

### API service variables

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `CORS_ORIGINS` | Frontend public URL (e.g. `https://….up.railway.app`) |
| `OPENAI_API_KEY` | Optional; enables Ask |
| `OPENAI_MODEL` | Optional (default `gpt-4o-mini`) |

### Frontend service variables

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | API public URL (e.g. `https://….up.railway.app`) |

`VITE_API_BASE_URL` is baked in at build time — set it before the first deploy (or redeploy after changing it).

`backend/railway.toml` and `frontend/railway.toml` define migrate/start and build/start commands.
