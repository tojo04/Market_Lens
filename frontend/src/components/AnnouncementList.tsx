import { useQuery } from "@tanstack/react-query";

import { getRecentAnnouncements } from "../api/announcements";
import type { AnnouncementSummary, CompanyMatch } from "../types/market";

interface AnnouncementListProps {
  company: CompanyMatch;
  selectedAnnouncement: AnnouncementSummary | null;
  onSelect: (announcement: AnnouncementSummary) => void;
}

export function AnnouncementList({
  company,
  selectedAnnouncement,
  onSelect,
}: AnnouncementListProps) {
  const announcementsQuery = useQuery({
    queryKey: ["announcements", company.company_id],
    queryFn: ({ signal }) => getRecentAnnouncements(company.company_id, signal),
    retry: 1,
  });

  return (
    <section className="panel" aria-labelledby="announcement-title">
      <div className="step-label">Step 2</div>
      <h2 id="announcement-title">Recent BSE announcements</h2>
      <p className="muted">Official filings for {company.company_name}</p>

      {announcementsQuery.isPending && <p role="status">Finding announcements…</p>}
      {announcementsQuery.isError && (
        <div className="fallback" role="alert">
          <strong>Automatic retrieval is unavailable.</strong>
          <span>You can continue with an official NSE/BSE PDF using the fallback below.</span>
        </div>
      )}
      {announcementsQuery.data?.items.length === 0 && (
        <p className="muted">No announcements were found in the recent bounded window.</p>
      )}
      {announcementsQuery.data && announcementsQuery.data.items.length > 0 && (
        <ul className="result-list announcement-list" aria-label="Recent announcements">
          {announcementsQuery.data.items.map((announcement) => {
            const selected = selectedAnnouncement?.announcement_id === announcement.announcement_id;
            return (
              <li key={announcement.announcement_id}>
                <button
                  type="button"
                  className={selected ? "result-button selected" : "result-button"}
                  onClick={() => onSelect(announcement)}
                  aria-pressed={selected}
                >
                  <span>{announcement.title}</span>
                  <small>
                    {announcement.category ?? "Uncategorized"} ·{" "}
                    {new Intl.DateTimeFormat("en-IN", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(announcement.published_at))}
                  </small>
                  <small>
                    {announcement.attachment_url ? "PDF attachment available" : "No PDF attachment"}
                  </small>
                </button>
              </li>
            );
          })}
        </ul>
      )}

    </section>
  );
}
