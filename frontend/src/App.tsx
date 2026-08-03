import "./app.css";

function App() {
  return (
    <main className="app-shell">
      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">Indian market announcements, made clearer</p>
        <h1 id="page-title">MarketLens AI</h1>
        <p className="summary">
          A focused educational tool for understanding official BSE and NSE corporate
          announcements and their nearby price reaction.
        </p>
        <div className="status" role="status">
          <span aria-hidden="true" className="status-dot" />
          Phase 0 scaffold is ready
        </div>
      </section>

      <section className="scope" aria-labelledby="scope-title">
        <h2 id="scope-title">What comes next</h2>
        <p>
          Company search, official announcement retrieval, and document analysis will be added
          one tested phase at a time.
        </p>
        <p className="disclaimer">
          Educational explanation only. MarketLens AI will not provide trade recommendations.
        </p>
      </section>
    </main>
  );
}

export default App;

