# Offline evaluation

The evaluation set contains eight synthetic, locally redistributable announcement
fixtures—one for every supported category. Each case includes page-aware source
text, reviewed source metadata, and a recorded candidate analysis. It never calls
BSE, yfinance, or OpenAI.

Run it from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m evaluation.run_evaluation
```

Use `--json` for a machine-readable report. Deterministic checks cover schema,
disclaimer, recommendation language, price arithmetic, fact citations, numeric
grounding, duplicate bullets, empty sections, category, company, date, and source
attribution.

The harness does not prove factual quality on real filings. For a real evaluation,
replace or supplement the synthetic cases with locally obtained official PDFs,
record source metadata without redistributing documents when licensing is unclear,
and complete `human_review_template.csv` after reviewing every output.
