# Demo data

This directory does not redistribute exchange PDFs. Use an official BSE/NSE filing
you are permitted to access, or generate the clearly synthetic text PDF supplied
for the manual-upload demonstration.

From the repository root:

```powershell
backend\.venv\Scripts\python.exe sample-data\generate_demo_pdf.py
```

This creates the ignored file `sample-data/demo-financial-results.pdf`. Upload it
with:

- Symbol: `DEMO`
- Exchange: `BSE`
- Announcement date: `2026-08-03`
- Company name: `MarketLens Demo Industries Limited`
- Security code: leave blank

The file is synthetic and must not be presented as an exchange filing or a real
company disclosure. It is suitable only for testing PDF extraction, fallback UI,
and local setup before a valid OpenAI API key is configured.
