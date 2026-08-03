import "./app.css";
import { useState } from "react";

import { CompanySearch } from "./components/CompanySearch";
import { AnnouncementList } from "./components/AnnouncementList";
import { AttachmentActions } from "./components/AttachmentActions";
import type { AnnouncementSummary, CompanyMatch } from "./types/market";

function App() {
  const [selectedCompany, setSelectedCompany] = useState<CompanyMatch | null>(null);
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<AnnouncementSummary | null>(null);

  const selectCompany = (company: CompanyMatch) => {
    setSelectedCompany(company);
    setSelectedAnnouncement(null);
  };

  return (
    <main className="app-shell">
      <header className="intro" aria-labelledby="page-title">
        <p className="eyebrow">Indian market announcements, made clearer</p>
        <h1 id="page-title">MarketLens AI</h1>
        <p className="summary">
          A focused educational tool for understanding official BSE and NSE corporate
          announcements and their nearby price reaction.
        </p>
      </header>

      <CompanySearch selectedCompany={selectedCompany} onSelect={selectCompany} />

      {selectedCompany ? (
        <AnnouncementList
          company={selectedCompany}
          selectedAnnouncement={selectedAnnouncement}
          onSelect={setSelectedAnnouncement}
        />
      ) : (
        <section className="panel waiting" aria-label="Announcement selection unavailable">
          <div className="step-label">Step 2</div>
          <h2>Recent BSE announcements</h2>
          <p className="muted">Select a supported company to continue.</p>
        </section>
      )}

      <AttachmentActions company={selectedCompany} announcement={selectedAnnouncement} />

      <footer className="disclaimer">
        Educational explanation only. MarketLens AI does not provide trade recommendations.
      </footer>
    </main>
  );
}

export default App;
