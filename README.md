# MarketLens AI

MarketLens AI is a focused educational application for explaining official Indian stock-market corporate announcements. The MVP will use a React frontend, a FastAPI backend, deterministic data services, and one bounded analysis agent.

The project currently implements through **Phase 8**: normalized provider contracts,
local company resolution, bounded official BSE announcement retrieval, secure PDF
download/upload and extraction, deterministic nearby price-reaction calculation,
and one structured announcement-analysis agent exposed through complete automatic
and manual-upload API workflows. The responsive frontend now presents the complete
search, selection, analysis, source-attribution, and PDF-fallback experience.
Persistence is intentionally not present yet.

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
# Set OPENAI_API_KEY in .env before requesting an analysis.
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

Search for a supported company, explicitly select one recent announcement, and
choose **Analyze announcement**. If exchange retrieval is unavailable, expand
**Upload official announcement PDF instead** and provide the filing metadata.

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

Available endpoints:

- `GET /api/health`
- `GET /api/companies/search?q=infosys`
- `GET /api/companies/{company_id}/announcements`
- `POST /api/companies/{company_id}/announcements/{announcement_id}/extract`
- `POST /api/documents/extract-upload`
- `POST /api/analyses/from-announcement`
- `POST /api/analyses/from-upload`

The health endpoint returns:

```json
{
  "status": "ok",
  "service": "MarketLens AI API"
}
```

Every backend response includes an `X-Request-ID` header. Browser access is restricted to origins configured through `MARKETLENS_CORS_ORIGINS`.

## Scope and safety

MarketLens AI explains public information; it does not provide investment advice, price forecasts, or trade recommendations. Remote attachment URLs are resolved server-side from selected announcements, validated against SSRF-sensitive destinations and redirects, streamed with size limits, checked for PDF content and signature, and deleted after extraction. Scanned PDFs return an explicit unsupported status because OCR is outside the MVP.

The single analysis agent receives only normalized metadata and bounded, extracted
document text. It can call only the internal price-reaction tool, whose arguments
and output are validated. The tool uses a bounded event window and application
arithmetic, and returns unavailable instead of guessing when a ticker or adjacent
trading session cannot be verified. A price reaction is not presented as proof
that an announcement caused a market move. Automated tests use a mocked OpenAI
client and never require an API key.

## BSE provider deployment note

The prototype announcement adapter uses BSE's official corporate-announcement JSON surface with bounded dates, limits, timeouts, a descriptive user agent, and no browser automation. BSE terms, allowed usage, rate limits, and endpoint behavior must be verified before any public deployment. Provider failures are surfaced explicitly and the interface retains a manual-upload fallback; the application never switches to an unofficial mirror.

The yfinance adapter is a replaceable prototype and must also be reviewed for suitability, licensing, reliability, and symbol coverage before deployment. Automated tests never contact BSE or yfinance.
