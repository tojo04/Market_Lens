# Two-minute placement demo

## Prepare

1. Run `scripts\setup.ps1` once.
2. Add `OPENAI_API_KEY` to `backend\.env`.
3. Start the backend from `backend/` with `uvicorn app.main:app --reload`.
4. Start the frontend from `frontend/` with `npm run dev`.
5. Keep `backend\.venv\Scripts\python.exe -m evaluation.run_evaluation` ready in a third terminal.

Because exchange availability changes, identify a supported company with at least
one recent PDF attachment before the interview. Keep an official PDF available for
the fallback; do not redistribute it unless permitted.

## Primary flow

1. Search for a known company such as Infosys or its BSE code `500209`.
2. Explicitly select the company and explain that resolution uses a bounded local master.
3. Select a recent announcement that shows “PDF available.”
4. Choose **Analyze announcement** and narrate only the high-level activity labels.
5. Show the grounded summary, page-aware facts, risks, limitations, confidence, and source links.
6. Show the previous/next trading-session closes and explain that reaction is not causation.
7. Scroll to history and reopen the saved result to demonstrate persistence.
8. Run the offline evaluation command and show the test summary.

## Fallback flow

If BSE retrieval is unavailable, expand **Upload official announcement PDF instead**.
Upload a permitted official filing and enter its metadata. For a setup-only test,
generate the clearly synthetic fixture described in `sample-data/README.md`.

## Interview talking points

- Automatic ingestion removes manual download friction while preserving official source URLs.
- Provider parsing stays outside the model so retrieval remains deterministic and testable.
- A local company master prevents the application from silently guessing ambiguous identities.
- The client never supplies an arbitrary download URL; the backend resolves the selected filing.
- SSRF defenses reject loopback/private addresses, unsafe redirects, large files, and fake PDFs.
- The model does not perform price arithmetic; application code calculates the percentage.
- PDF text is untrusted evidence and document instructions are never followed.
- Strict structured outputs reduce shape failures, then Pydantic validates the result again.
- Bounded session lookup handles weekends and holidays without inventing prices.
- Nearby movement is described as reaction, never proof that the filing caused the move.
- Manual upload keeps the core workflow usable when an exchange provider fails.
- One agent is enough because retrieval, extraction, calculation, and persistence are services.
- Output validators and prompts prohibit buy/sell/hold calls, targets, and stop losses.

## Honest closing

This is a small educational MVP. It does not guarantee factual correctness, support
OCR, cover every listed company, provide live exchange-grade market data, or offer
investment advice. The architecture is intentionally narrow enough to explain and test.
