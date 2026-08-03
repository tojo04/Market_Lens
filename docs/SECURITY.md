# Security model

MarketLens processes public corporate announcements but treats every remote URL,
PDF byte, extracted page, model tool call, and model response as untrusted.

## Trust boundaries

- The browser may choose only a provider, company ID, and announcement ID for automatic analysis.
- The backend re-resolves the announcement and attachment URL through the configured provider.
- The model receives bounded extracted text and normalized metadata, never arbitrary network access.
- The only model tool is the validated deterministic price-reaction function.
- Only validated final analysis JSON is persisted; PDFs and full extracted documents are not saved.

## Attachment controls

- HTTP/HTTPS protocols only.
- DNS resolution before requests and after every bounded redirect.
- Loopback, private, link-local, multicast, reserved, and unspecified addresses rejected.
- Explicit connect/read/write/pool timeouts and download-size limits.
- Content type and `%PDF-` signature validation; HTML masquerading as PDF rejected.
- Generated temporary names and cleanup after success or failure.
- PDF page limit and scanned/image-only detection; no embedded content is executed.

## Model controls

- Source text is labeled untrusted and document instructions are ignored.
- Only one bounded tool call is permitted by default.
- Tool name, identifier, exchange, symbol/security code, and date are validated against source metadata.
- Strict JSON schema plus Pydantic validation protects the final response shape.
- Source metadata and price reaction are replaced with authoritative application values.
- Trade-recommendation phrases, target prices, and stop losses are rejected.
- Document text, binary data, hidden reasoning, and API keys are not logged or stored.

## Deployment checklist

- Use HTTPS through a trusted reverse proxy.
- Set a non-placeholder contact in the outbound user agent.
- Restrict `MARKETLENS_CORS_ORIGINS` to the deployed frontend.
- Store `OPENAI_API_KEY` in a managed secret store, never a committed file.
- Put the SQLite file on protected storage or replace it with an approved database if concurrency grows.
- Review BSE and yfinance terms, licensing, rate limits, availability, and attribution requirements.
- Add authentication before exposing saved history to multiple or untrusted users.
- Add retention and deletion policies before storing production user data.
- Run `scripts\check.ps1` and a dependency/security review before release.

To report a vulnerability, provide reproducible details privately to the repository owner.
