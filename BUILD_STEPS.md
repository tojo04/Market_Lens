# BUILD_STEPS.md

## MarketLens AI build plan

This project is a focused, single-agent application for Indian stock-market corporate announcements.

### Primary workflow

```text
Search company
    ↓
Fetch recent official BSE announcements
    ↓
Select announcement
    ↓
Download attachment
    ↓
Extract PDF text
    ↓
Single AI agent analyzes it
    ↓
Calculate nearby price reaction
    ↓
Display and save result
```

### Fallback workflow

```text
Automatic retrieval fails
    ↓
Upload official NSE/BSE PDF manually
    ↓
Analyze using the same pipeline
```

Build one phase at a time. Give Codex only the current phase.

---

# Phase 0 — Repository setup

## Goal

Create the React/FastAPI monorepo and basic development tooling.

## Tasks

1. Create:
   - `frontend/`
   - `backend/`
   - `sample-data/`
2. Preserve `AGENTS.md` and this file at the root.
3. Add `.gitignore`.
4. Scaffold React + Vite + TypeScript.
5. Scaffold FastAPI.
6. Add `GET /api/health`.
7. Add `.env.example`.
8. Add root `README.md`.
9. Configure:
   - pytest,
   - ruff,
   - frontend linting,
   - strict TypeScript.

## Suggested backend dependencies

- fastapi
- uvicorn
- pydantic
- pydantic-settings
- python-multipart
- httpx
- feedparser
- beautifulsoup4
- pymupdf
- pandas
- yfinance
- sqlalchemy
- openai
- pytest
- respx
- ruff

## Suggested frontend dependencies

- react
- react-dom
- typescript
- vite
- @tanstack/react-query
- react-hook-form
- zod
- @hookform/resolvers
- tailwindcss

## Acceptance criteria

- Backend starts.
- Health endpoint works.
- Frontend starts.
- Backend tests run.
- Frontend lint and type-check run.
- No external API or scraping is implemented.

## Codex prompt

```text
Read AGENTS.md and Phase 0 of BUILD_STEPS.md. Scaffold only Phase 0.
Create a React + Vite + TypeScript frontend and a FastAPI backend with a typed
health endpoint, environment examples, linting, testing, and local startup
instructions. Do not implement company search, announcement retrieval, PDF
processing, market data, OpenAI integration, persistence, or later phases.
Run the relevant checks and report exact results.
```

---

# Phase 1 — Domain schemas and provider contracts

## Goal

Define stable models before writing provider-specific code.

## Tasks

1. Create normalized Pydantic models:
   - `CompanyMatch`
   - `AnnouncementSummary`
   - `DownloadedAttachment`
   - `PageText`
   - `ExtractionResult`
   - `DailyClose`
   - `PriceReaction`
2. Define provider interfaces:
   - `AnnouncementProvider`
   - `MarketDataProvider`
3. Define domain exceptions:
   - `ProviderUnavailableError`
   - `ProviderRateLimitError`
   - `CompanyNotFoundError`
   - `AmbiguousCompanyError`
   - `AnnouncementNotFoundError`
   - `AttachmentUnavailableError`
   - `UnsafeDownloadError`
   - `InvalidDocumentError`
4. Add configuration values:
   - provider base URL,
   - user agent,
   - timeout,
   - maximum results,
   - maximum download size,
   - maximum PDF pages.
5. Write schema and contract tests.

## Important rule

Do not implement BSE parsing yet. This phase creates boundaries so provider code can later be replaced.

## Acceptance criteria

The backend contains typed, tested provider contracts with no external calls.

## Codex prompt

```text
Read AGENTS.md and Phase 1 of BUILD_STEPS.md. Implement only normalized domain
schemas, provider protocols, configuration, and domain exceptions. Do not make
network requests or implement BSE, PDF extraction, market data, OpenAI, routes,
or frontend changes beyond any required shared type placeholders. Add tests.
```

---

# Phase 2 — Company resolution

## Goal

Allow users to search for a listed company without ambiguous ticker guessing.

## Recommended MVP approach

Use a small local company-master dataset for supported companies.

Start with:

- NIFTY 50 companies, or
- 50–100 frequently traded BSE/NSE companies.

The dataset should contain:

- company name,
- aliases,
- BSE security code,
- NSE symbol where known,
- provider company ID,
- exchange.

This avoids unreliable free-text scraping for company identity.

## Backend tasks

1. Add a local CSV or JSON company master.
2. Add a `CompanyRepository`.
3. Implement:
   - exact security-code match,
   - exact symbol match,
   - normalized name match,
   - alias match,
   - limited fuzzy matching.
4. Add:

```http
GET /api/companies/search?q=infosys
```

5. Return at most 10 results.
6. Never auto-select when multiple strong matches exist.

## Frontend tasks

1. Add a company-search box.
2. Debounce requests.
3. Show company name, symbol, security code, and exchange.
4. Require the user to choose a result.

## Tests

- Exact name
- Case-insensitive name
- Security-code match
- Symbol match
- Alias match
- No match
- Ambiguous match
- Result limit
- Empty query rejection

## Acceptance criteria

A user can reliably select a supported company without the backend guessing.

## Codex prompt

```text
Read AGENTS.md and Phase 2 of BUILD_STEPS.md. Implement only local company
resolution using a small checked-in company-master dataset and a typed search
endpoint. Add a debounced frontend company selector. Do not implement automatic
announcement retrieval, remote scraping, PDFs, market data, OpenAI, or history.
Run tests, linting, and type checks.
```

---

# Phase 3 — Automatic BSE announcement retrieval

## Goal

Fetch and normalize recent BSE corporate announcements for a selected company.

## Implementation guidance

Use an official feed, structured endpoint, or allowed public source where possible.

Do not:

- automate a browser,
- bypass anti-bot controls,
- spoof sessions,
- solve CAPTCHAs,
- rotate proxies,
- or depend on undocumented browser-only behavior without a fallback.

Keep all provider-specific behavior in:

```text
backend/app/providers/announcements/bse.py
```

## Backend tasks

1. Implement `BSEAnnouncementProvider`.
2. Add bounded HTTP timeouts.
3. Add a descriptive user agent.
4. Parse provider data into `AnnouncementSummary`.
5. Filter by:
   - company/security code,
   - optional date range,
   - result limit.
6. Preserve:
   - announcement ID,
   - title,
   - category,
   - published timestamp,
   - official detail URL,
   - attachment URL.
7. Add:

```http
GET /api/companies/{company_id}/announcements
```

8. Return a typed provider-unavailable error when retrieval fails.
9. Add a note in code and README that provider terms and endpoint behavior must be verified before public deployment.
10. Do not download attachments yet.

## Frontend tasks

1. After company selection, load recent announcements.
2. Show:
   - title,
   - category,
   - published date/time,
   - attachment availability.
3. Let the user select one announcement.
4. Show a manual-upload fallback when the provider fails.

## Tests

Use mocked HTTP fixtures:

- Valid feed/response
- Empty results
- Company filtering
- Date filtering
- Missing title
- Missing attachment
- Duplicate announcements
- Malformed feed
- Timeout
- Rate limit
- Unexpected provider schema
- Result-limit enforcement

## Acceptance criteria

A selected supported company displays normalized recent BSE announcements without calling the AI model.

## Codex prompt

```text
Read AGENTS.md and Phase 3 of BUILD_STEPS.md. Implement only automatic BSE
announcement retrieval behind the AnnouncementProvider interface. Use bounded
HTTP calls, normalize results, preserve source URLs, add a typed endpoint, and
build the announcement list UI with a manual-upload fallback state. Mock all
external calls in tests. Do not download PDFs, call OpenAI, fetch price data,
or add persistence.
```

---

# Phase 4 — Secure attachment download and PDF extraction

## Goal

Download the selected official attachment safely and extract page-aware text.

## Backend tasks

1. Implement `AttachmentService`.
2. Validate remote URLs:
   - only HTTPS where possible,
   - reject localhost,
   - reject private IP ranges,
   - restrict redirects,
   - enforce timeout,
   - enforce maximum size.
3. Validate:
   - content type,
   - PDF signature,
   - non-empty body.
4. Save to a generated temporary file.
5. Extract using PyMuPDF.
6. Return:
   - page count,
   - page-aware text,
   - warnings,
   - extraction status.
7. Detect scanned/image-only PDFs.
8. Return `scanned_pdf_unsupported`.
9. Always clean temporary files.
10. Add a development-only service test route only if necessary; remove it before release.

## Manual-upload tasks

1. Add a reusable upload endpoint/service.
2. Apply the same PDF validation and extraction rules.
3. Keep both automatic and manual flows on the same extraction path.

## Frontend tasks

1. Add:
   - “Analyze selected announcement”
   - “Upload PDF instead”
2. Show download/extraction loading states.
3. Show useful errors:
   - attachment unavailable,
   - invalid PDF,
   - oversized file,
   - scanned PDF unsupported.

## Tests

- Valid PDF download
- Redirect
- Excessive redirects
- Oversized file
- Invalid content type
- HTML disguised as PDF
- Private IP rejection
- Timeout
- Empty file
- Valid text extraction
- Scanned PDF unsupported
- Temporary cleanup
- Manual upload using same extractor

## Acceptance criteria

The backend can securely download and extract a selected announcement attachment, while manual upload remains functional.

## Codex prompt

```text
Read AGENTS.md and Phase 4 of BUILD_STEPS.md. Implement secure remote attachment
download with SSRF protections and page-aware PDF extraction. Reuse the same
extractor for the manual-upload fallback. Add typed errors, cleanup, UI states,
and comprehensive mocked tests. Do not add market data, OpenAI analysis,
persistence, OCR, or later phases.
```

---

# Phase 5 — Deterministic market-price tool

## Goal

Calculate the nearby stock-price reaction without using the model for arithmetic.

## Backend tasks

1. Implement a `MarketDataProvider`.
2. Add a prototype yfinance adapter.
3. Implement:

```text
get_price_reaction(
    symbol,
    exchange,
    announcement_date
)
```

4. Fetch a small event window.
5. Find:
   - previous trading date and close,
   - next trading date and close.
6. Calculate:

```text
((next_close - previous_close) / previous_close) * 100
```

7. Return typed status and notes.
8. Handle:
   - weekends,
   - holidays,
   - missing symbols,
   - missing data,
   - timeouts,
   - provider failures.
9. Return `unavailable` instead of guessing.

## Rules

- Use deterministic ticker mapping.
- Never silently substitute another company.
- Describe the result as price reaction, not causation.
- BSE-only companies may return unavailable if the prototype provider mapping is not reliable.

## Tests

Mock all provider calls:

- Normal weekday
- Weekend
- Holiday
- Missing data
- Invalid symbol
- Provider exception
- Correct percentage
- Zero denominator
- Rounding
- BSE unavailable path

## Acceptance criteria

A selected company and announcement date produce a valid price-reaction object or a clear unavailable result.

## Codex prompt

```text
Read AGENTS.md and Phase 5 of BUILD_STEPS.md. Implement only the deterministic
market-price provider and price-reaction service. Use yfinance as a replaceable
prototype adapter. Handle non-trading days and unavailable data. Mock all
external calls. Do not add OpenAI, final analysis, persistence, or charts.
```

---

# Phase 6 — Single structured analysis agent

## Goal

Create one AI agent that analyzes the extracted announcement and may call the price-reaction tool.

## Agent input

- Company metadata
- Announcement metadata
- Extracted page text
- Extraction warnings
- Announcement date
- Symbol/security code

## Agent tool

Initially expose only:

- `get_price_reaction`

Automatic retrieval and PDF extraction happen before the agent call.

## Backend tasks

1. Add OpenAI client through dependency injection.
2. Read:
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL`
3. Add prompts in a dedicated file.
4. Define final `AnnouncementAnalysis` Pydantic schema.
5. Implement bounded function calling:
   - maximum tool calls,
   - timeout,
   - validated arguments,
   - malformed-call handling,
   - final-output validation.
6. Treat document text as untrusted.
7. Ignore instructions found inside the PDF.
8. Limit document length safely.
9. Return controlled validation errors.
10. Do not expose hidden reasoning.

## Required output behavior

- Facts must be grounded in document text or tool output.
- Preserve ₹ crore, ₹ lakh, percentages, and dates.
- Include page numbers/source excerpts for important facts where possible.
- Mark uncertainty.
- Explain unavailable price data.
- Never recommend buying or selling.
- Include:

```text
This is an educational explanation of public information, not investment advice.
```

## Tests

Mock OpenAI:

- Valid structured result
- Tool call and final result
- Invalid tool arguments
- Excess tool calls
- Invalid schema
- Prompt injection in source text
- No trade recommendation
- Correct source metadata
- Indian-unit preservation
- Unknown category maps to `other`

## Acceptance criteria

The backend can produce a validated structured analysis from extracted announcement text using one agent.

## Codex prompt

```text
Read AGENTS.md and Phase 6 of BUILD_STEPS.md. Implement one structured
announcement-analysis agent using the OpenAI Responses API and function calling.
Expose only the existing price-reaction tool. Treat PDF text as untrusted data,
validate all tool arguments and final output, cap tool calls, and mock OpenAI in
tests. Do not add multiple agents, generic browsing, RAG, persistence, or new
provider integrations.
```

---

# Phase 7 — Complete automatic-analysis API

## Goal

Connect company selection, announcement retrieval, attachment download, extraction, agent analysis, and price reaction.

## Backend endpoints

### Analyze selected announcement

```http
POST /api/analyses/from-announcement
```

Input:

```json
{
  "provider": "bse",
  "company_id": "...",
  "announcement_id": "..."
}
```

### Analyze uploaded fallback

```http
POST /api/analyses/from-upload
Content-Type: multipart/form-data
```

Fields:

- file
- symbol
- exchange
- announcement_date
- company_name, optional
- security_code, optional

## Backend tasks

1. Resolve the selected announcement server-side.
2. Do not trust a client-supplied arbitrary attachment URL.
3. Download through the provider/service.
4. Extract the PDF.
5. Call the single agent.
6. Validate the final result.
7. Return a stable API shape.
8. Add request IDs.
9. Clean temporary files.
10. Use typed error codes.

## Error codes

- `company_not_found`
- `announcement_not_found`
- `provider_unavailable`
- `provider_rate_limited`
- `attachment_unavailable`
- `unsafe_attachment_url`
- `invalid_pdf`
- `file_too_large`
- `scanned_pdf_unsupported`
- `market_data_unavailable`
- `analysis_provider_error`
- `analysis_validation_error`

Market-data unavailability should usually produce a successful analysis with an unavailable price-reaction field.

## Integration tests

- Full automatic success flow
- Missing attachment
- Provider failure
- Provider timeout
- Unsafe attachment
- Scanned PDF
- Price unavailable
- OpenAI failure
- Invalid OpenAI output
- Manual-upload success
- Temporary cleanup

## Acceptance criteria

A user can select a retrieved announcement and receive a complete validated analysis from one API call.

## Codex prompt

```text
Read AGENTS.md and Phase 7 of BUILD_STEPS.md. Implement the complete automatic
analysis vertical slice. Resolve the selected announcement server-side, securely
download its attachment, extract it, invoke the existing single agent, and return
a stable typed result. Keep the manual-upload endpoint as fallback. Add request
IDs, typed errors, cleanup, and mocked integration tests. Do not add persistence,
authentication, or unrelated features.
```

---

# Phase 8 — Polished frontend

## Goal

Create a two-minute recruiter-friendly demonstration.

## UI flow

### Step 1 — Search company

- Search input
- Company suggestions
- Explicit selection

### Step 2 — Select announcement

- Recent announcements
- Title
- Category
- Published date
- Attachment status
- Analyze button

### Step 3 — Result

Show:

- Announcement title/category
- Summary
- Important facts
- Why it matters
- Positive signals
- Risks
- Price reaction
- Confidence
- Limitations
- Official source link
- Disclaimer

### Fallback

Always show:

- “Upload official announcement PDF instead”

## Activity states

Show high-level progress only:

- Finding announcements
- Downloading official attachment
- Extracting document
- Analyzing facts
- Checking nearby prices
- Preparing result

Do not show hidden chain-of-thought.

## UX requirements

- Debounced search
- Disable duplicate submissions
- Preserve selected company after recoverable errors
- Clear provider-unavailable message
- Clear fallback path
- Accessible form controls
- Responsive laptop/mobile layout
- Neutral visual design
- No green/red buy/sell implication
- Consistent Indian currency and date formatting

## Acceptance criteria

A recruiter can understand and run the full workflow without documentation.

## Codex prompt

```text
Read AGENTS.md and Phase 8 of BUILD_STEPS.md. Build the polished frontend around
the existing automatic-analysis APIs. Implement company search, announcement
selection, loading stages, structured results, source links, typed errors, and a
visible manual-upload fallback. Keep the UI focused and neutral. Do not add login,
watchlists, recommendations, dashboards, or unrelated features. Run linting,
type checks, tests, and a production build.
```

---

# Phase 9 — SQLite history

## Goal

Save and reopen completed analyses.

## Backend tasks

1. Add SQLite/SQLAlchemy persistence.
2. Save:
   - analysis ID,
   - company metadata,
   - announcement metadata,
   - validated result JSON,
   - created timestamp.
3. Do not save:
   - downloaded PDFs,
   - temporary paths,
   - hidden reasoning,
   - secrets.
4. Add:
   - `GET /api/analyses`
   - `GET /api/analyses/{id}`
   - optional delete endpoint.
5. Return newest first.
6. Add a small limit or pagination.

## Frontend tasks

1. Add analysis history.
2. Show:
   - company,
   - announcement title,
   - category,
   - announcement date,
   - analysis date.
3. Allow reopening a result.
4. Add empty state.

## Tests

- Save
- List
- Retrieve
- Missing ID
- Delete, if implemented
- Invalid stored data handling

## Acceptance criteria

Completed analyses survive application restart.

## Codex prompt

```text
Read AGENTS.md and Phase 9 of BUILD_STEPS.md. Add minimal SQLite persistence for
validated analysis results and a simple history UI. Do not store PDFs, temporary
files, secrets, or model reasoning. Do not add users, authentication, cloud
databases, watchlists, or unrelated features.
```

---

# Phase 10 — Evaluation and reliability

## Goal

Show that the AI feature is measured and tested.

## Evaluation set

Create 8–12 cases covering:

- Financial results
- Dividend
- Order/contract
- Acquisition/investment
- Management change
- Fundraising
- Corporate action
- Other

Use source metadata and local setup instructions when redistributing PDFs is uncertain.

## Evaluation dimensions

1. Correct category
2. Correct company
3. Correct date
4. Important facts grounded in PDF
5. Numeric values copied accurately
6. No fabricated values
7. Price arithmetic correct
8. Neutral risk language
9. No trade recommendation
10. Valid schema
11. Correct limitations
12. Correct source attribution

## Automated checks

- Schema validity
- Required disclaimer
- Prohibited recommendation phrases
- Recalculated percentage match
- Source excerpt/page number presence
- Duplicate bullet detection
- Empty-section detection
- Source metadata presence

## Human-review CSV

```text
case_id,category_correct,facts_correct,numbers_correct,no_hallucination,
neutral_language,source_correct,limitations_correct,notes
```

## Acceptance criteria

README includes an honest evaluation summary and known failure modes.

## Codex prompt

```text
Read AGENTS.md and Phase 10 of BUILD_STEPS.md. Add a repeatable evaluation
harness for the completed announcement-analysis workflow. Include deterministic
checks for schema, price arithmetic, source attribution, disclaimers, and
prohibited recommendation language, plus a human-review CSV template. Mock or
record external inputs appropriately. Do not fine-tune a model or add RAG.
```

---

# Phase 11 — Placement polish

## Goal

Make the project easy to run and explain.

## README sections

1. Problem
2. Solution
3. Why a single agent
4. Automatic retrieval workflow
5. Manual-upload fallback
6. Architecture diagram
7. Provider interfaces
8. Tool-calling workflow
9. Technology stack
10. Local setup
11. Environment variables
12. API contracts
13. Screenshots
14. Testing and evaluation
15. Security
16. Data-source and deployment considerations
17. Limitations
18. Future improvements

## Interview talking points

Be able to explain:

- Why automatic ingestion improves usability
- Why provider logic is outside the agent
- Why company resolution uses a local master
- Why arbitrary URLs are not accepted
- How SSRF is prevented
- Why the model does not perform arithmetic
- Why PDF text is treated as untrusted
- How structured outputs reduce failures
- How holidays and weekends are handled
- Why price reaction is not causation
- Why manual upload remains available
- Why one agent is enough
- Why no buy/sell recommendation is produced

## Demo flow

1. Search a known company.
2. Select it.
3. Load recent announcements.
4. Select one with an attachment.
5. Analyze it.
6. Show important extracted facts.
7. Show price reaction.
8. Show source and limitations.
9. Open a saved result.
10. Briefly show tests/evaluation.

## Final checks

### Backend

- Format
- Lint
- Tests
- No live paid API calls in tests
- No unrestricted external URL input

### Frontend

- Lint
- Type-check
- Production build
- Search/select/analyze flow
- Fallback upload flow

### Repository

- No `.env`
- No API keys
- No database file
- No downloaded PDFs
- No temporary files
- Clear setup instructions
- Clear limitations
- Working demo data

## Acceptance criteria

A new developer can clone the project, configure it, run it, and reproduce the demonstration.

## Codex prompt

```text
Read AGENTS.md and Phase 11 of BUILD_STEPS.md. Polish the existing project for a
campus-placement demonstration. Improve documentation, setup, accessibility,
security notes, error messages, tests, and demo flow without expanding scope.
Run every available check and report exact results and remaining limitations.
```

---

# Optional improvements after the MVP

Implement only after the full core workflow works.

## Option A — NSE provider

Add an NSE provider only through a compliant and maintainable data source. Do not bypass anti-bot controls.

## Option B — Larger company master

Expand beyond the initial supported list.

## Option C — Compare quarters

Upload or retrieve the previous quarter and summarize changes.

## Option D — OCR

Support scanned PDFs with confidence warnings.

## Option E — Event-window chart

Show closes for several sessions before and after the announcement.

## Option F — Export report

Export as Markdown or PDF.

## Option G — Scheduled watchlist

Notify users about new announcements only after the core application is complete and a suitable data source is available.

Do not add real-money trading.

---

# Recommended commit sequence

```text
chore: scaffold frontend and backend
feat: add domain schemas and provider contracts
feat: add company resolution
feat: retrieve BSE announcements
feat: secure attachment download and extraction
feat: add price reaction service
feat: add structured announcement agent
feat: connect automatic analysis workflow
feat: build announcement analysis interface
feat: persist analysis history
test: add evaluation harness
docs: prepare placement demo
```

---

# How to use Codex

Use one task per phase.

Base prompt:

```text
Read AGENTS.md and Phase N of BUILD_STEPS.md.
Inspect the current repository before editing.
Implement only this phase.
Run relevant checks.
Do not begin the next phase.
Report files changed, commands run, test results, and limitations.
```

After every Codex task:

1. Review the diff.
2. Run the application.
3. Test one success path.
4. Test one failure path.
5. Commit only after it works.
6. Move to the next phase.

Do not ask Codex to build the whole project in one prompt.
