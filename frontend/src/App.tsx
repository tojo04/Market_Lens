import "./app.css";
import { useEffect, useRef, useState } from "react";

import { AnalysisActions } from "./components/AnalysisActions";
import { AnalysisHistory } from "./components/AnalysisHistory";
import { AnalysisResult } from "./components/AnalysisResult";
import { AnnouncementList } from "./components/AnnouncementList";
import { CompanySearch } from "./components/CompanySearch";
import type { AnnouncementAnalysis, AnnouncementSummary, CompanyMatch } from "./types/market";

function App() {
  const [selectedCompany, setSelectedCompany] = useState<CompanyMatch | null>(null);
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<AnnouncementSummary | null>(null);
  const [completedAnalysis, setCompletedAnalysis] = useState<{
    contextKey: string;
    result: AnnouncementAnalysis;
  } | null>(null);
  const contextKey = `${selectedCompany?.company_id ?? "none"}:${selectedAnnouncement?.announcement_id ?? "none"}`;
  const analysis = completedAnalysis?.contextKey === contextKey ? completedAnalysis.result : null;
  const resultAnchor = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!analysis || !resultAnchor.current) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    resultAnchor.current.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "start",
    });
    resultAnchor.current.focus({ preventScroll: true });
  }, [analysis]);

  const selectCompany = (company: CompanyMatch) => {
    setSelectedCompany(company);
    setSelectedAnnouncement(null);
    setCompletedAnalysis(null);
  };

  const selectAnnouncement = (announcement: AnnouncementSummary) => {
    setSelectedAnnouncement(announcement);
    setCompletedAnalysis(null);
  };

  return (
    <main className="app-shell">
      <a className="skip-link" href="#company-query">Skip to company search</a>
      <header className="intro" aria-labelledby="page-title">
        <p className="eyebrow">Indian market announcements, made clearer</p>
        <h1 id="page-title">MarketLens AI</h1>
        <p className="summary">
          Turn one official corporate announcement into a clear, source-grounded explanation —
          with the nearby market reaction kept in context.
        </p>
        <div className="intro-notes" aria-label="Product boundaries">
          <span>Official exchange filings</span>
          <span>Page-aware facts</span>
          <span>No buy or sell calls</span>
        </div>
      </header>

      <div className="selection-grid">
        <CompanySearch selectedCompany={selectedCompany} onSelect={selectCompany} />

        {selectedCompany ? (
          <AnnouncementList
            company={selectedCompany}
            selectedAnnouncement={selectedAnnouncement}
            onSelect={selectAnnouncement}
          />
        ) : (
          <section className="panel waiting" aria-label="Announcement selection unavailable">
            <div className="step-label">Step 2</div>
            <h2>Choose a recent announcement</h2>
            <p className="muted">Select a supported company to load its official BSE filings.</p>
          </section>
        )}
      </div>

      <AnalysisActions
        key={contextKey}
        company={selectedCompany}
        announcement={selectedAnnouncement}
        onComplete={(result) => setCompletedAnalysis({ contextKey, result })}
      />

      {analysis && (
        <div className="result-anchor" ref={resultAnchor} tabIndex={-1}>
          <AnalysisResult analysis={analysis} />
        </div>
      )}

      <AnalysisHistory
        onOpen={(result) => setCompletedAnalysis({ contextKey, result })}
      />

      <footer className="disclaimer">
        MarketLens AI analyzes one supplied public filing at a time. It does not predict prices or
        provide investment recommendations.
      </footer>
    </main>
  );
}

export default App;
