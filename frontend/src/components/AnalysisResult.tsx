import type { AnnouncementAnalysis } from "../types/market";

interface AnalysisResultProps {
  analysis: AnnouncementAnalysis;
}

const CATEGORY_LABELS: Record<AnnouncementAnalysis["announcement_category"], string> = {
  financial_results: "Financial results",
  dividend: "Dividend",
  order_or_contract: "Order or contract",
  acquisition_or_investment: "Acquisition or investment",
  management_change: "Management or board change",
  fundraising: "Fundraising",
  corporate_action: "Corporate action",
  other: "Other announcement",
};

const dateFormatter = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });
const priceFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const percentageFormatter = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: "always",
});

function formatDate(value: string | null): string {
  if (!value) return "Unavailable";
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : dateFormatter.format(date);
}

function safeExternalUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function InsightList({ items, emptyText }: { items: string[]; emptyText: string }) {
  if (items.length === 0) return <p className="muted">{emptyText}</p>;
  return (
    <ul className="insight-list">
      {items.map((item, index) => (
        <li key={`${index}-${item}`}>{item}</li>
      ))}
    </ul>
  );
}

export function AnalysisResult({ analysis }: AnalysisResultProps) {
  const sourceUrl = safeExternalUrl(analysis.source.announcement_url);
  const attachmentUrl = safeExternalUrl(analysis.source.attachment_url);
  const price = analysis.price_reaction;

  return (
    <article className="analysis-result" aria-labelledby="analysis-result-title" tabIndex={-1}>
      <header className="result-hero">
        <div className="result-kicker">
          <span>{CATEGORY_LABELS[analysis.announcement_category]}</span>
          <span>{analysis.confidence} confidence</span>
        </div>
        <h2 id="analysis-result-title">{analysis.title}</h2>
        <p>{analysis.summary}</p>
        <div className="source-line">
          <span>{analysis.source.company_name}</span>
          <span>{analysis.source.exchange}</span>
          <span>{formatDate(analysis.source.published_at)}</span>
        </div>
      </header>

      <section className="result-section" aria-labelledby="facts-title">
        <div className="result-section-heading">
          <span>01</span>
          <h3 id="facts-title">Important facts and numbers</h3>
        </div>
        {analysis.important_facts.length > 0 ? (
          <div className="fact-grid">
            {analysis.important_facts.map((fact, index) => (
              <div className="fact-card" key={`${index}-${fact.label}`}>
                <span>{fact.label}</span>
                <strong>{fact.value}</strong>
                {fact.source_excerpt && <blockquote>“{fact.source_excerpt}”</blockquote>}
                {fact.page_number && <small>Page {fact.page_number}</small>}
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No specific figures were identified in the supplied filing.</p>
        )}
      </section>

      <div className="insight-grid">
        <section className="result-section" aria-labelledby="matters-title">
          <div className="result-section-heading">
            <span>02</span>
            <h3 id="matters-title">Why it matters</h3>
          </div>
          <InsightList items={analysis.why_it_matters} emptyText="No material context was identified." />
        </section>
        <section className="result-section" aria-labelledby="signals-title">
          <div className="result-section-heading">
            <span>03</span>
            <h3 id="signals-title">Possible positive signals</h3>
          </div>
          <InsightList items={analysis.positive_signals} emptyText="No positive signals were identified." />
        </section>
        <section className="result-section" aria-labelledby="risks-title">
          <div className="result-section-heading">
            <span>04</span>
            <h3 id="risks-title">Risks and concerns</h3>
          </div>
          <InsightList items={analysis.risks} emptyText="No specific risks were identified in the filing." />
        </section>
      </div>

      <section className="result-section price-section" aria-labelledby="price-title">
        <div className="result-section-heading">
          <span>05</span>
          <h3 id="price-title">Nearby price reaction</h3>
        </div>
        {price.status === "available" &&
        price.previous_close !== null &&
        price.next_close !== null &&
        price.percentage_change !== null ? (
          <div className="price-comparison">
            <div>
              <span>Previous session · {formatDate(price.previous_trading_date)}</span>
              <strong>{priceFormatter.format(price.previous_close)}</strong>
            </div>
            <div className="price-change">
              <span>Nearby change</span>
              <strong>{percentageFormatter.format(price.percentage_change)}%</strong>
            </div>
            <div>
              <span>Next session · {formatDate(price.next_trading_date)}</span>
              <strong>{priceFormatter.format(price.next_close)}</strong>
            </div>
          </div>
        ) : (
          <div className="unavailable-state">
            <strong>Price reaction unavailable</strong>
            <span>{price.note ?? "There was not enough verified market data to calculate it."}</span>
          </div>
        )}
        {price.status === "available" && price.note && <p className="price-note">{price.note}</p>}
      </section>

      <section className="result-section result-footer" aria-labelledby="limitations-title">
        <div>
          <div className="result-section-heading">
            <span>06</span>
            <h3 id="limitations-title">Limitations</h3>
          </div>
          <InsightList items={analysis.limitations} emptyText="No additional limitations were returned." />
        </div>
        <div className="source-card">
          <span>Source metadata</span>
          <strong>{analysis.source.provider === "manual_upload" ? "Manual official PDF" : "BSE filing"}</strong>
          <small>
            {analysis.source.symbol ?? analysis.source.security_code ?? "Symbol unavailable"} · {analysis.source.exchange}
          </small>
          <div className="source-links">
            {sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer">Official announcement</a>}
            {attachmentUrl && <a href={attachmentUrl} target="_blank" rel="noreferrer">Official PDF</a>}
            {!sourceUrl && !attachmentUrl && <span>Analyzed from the uploaded file.</span>}
          </div>
        </div>
      </section>

      <footer className="analysis-disclaimer">{analysis.disclaimer}</footer>
    </article>
  );
}
