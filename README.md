# MarketLens AI

MarketLens AI is a focused educational application for explaining official Indian stock-market corporate announcements. The MVP will use a React frontend, a FastAPI backend, deterministic data services, and one bounded analysis agent.

This repository currently implements **Phase 0 only**: the frontend/backend scaffold and development tooling. Company resolution, exchange retrieval, PDF processing, market data, model calls, and persistence are intentionally not present yet.

## Prerequisites

- Python 3.12 or newer
- Node.js 20.19 or newer
- npm 10 or newer

## Run the backend

From the repository root in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Check it with:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

Interactive API documentation is available at `http://localhost:8000/docs`.

## Run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Checks

Backend:

```powershell
cd backend
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Frontend:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build
```

## Current API

`GET /api/health` returns a typed response:

```json
{
  "status": "ok",
  "service": "MarketLens AI API"
}
```

Every backend response includes an `X-Request-ID` header. Browser access is restricted to origins configured through `MARKETLENS_CORS_ORIGINS`.

## Scope and safety

MarketLens AI will explain public information; it will not provide investment advice, price forecasts, or trade recommendations. External retrieval and AI analysis are deliberately deferred to later build phases so their provider, security, and test boundaries can be implemented explicitly.

