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
