import { useMutation, useQuery } from "@tanstack/react-query";

import { getAnalysisHistory, getSavedAnalysis } from "../api/analyses";
import { ApiError } from "../api/client";
import type { AnnouncementAnalysis, AnnouncementCategory } from "../types/market";

interface AnalysisHistoryProps {
  onOpen: (analysis: AnnouncementAnalysis) => void;
}

const dateFormatter = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });
const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDate(value: string | null, includeTime = false): string {
  if (!value) return "Date unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Date unavailable";
  return includeTime ? dateTimeFormatter.format(parsed) : dateFormatter.format(parsed);
}

function formatCategory(category: AnnouncementCategory): string {
  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function AnalysisHistory({ onOpen }: AnalysisHistoryProps) {
  const historyQuery = useQuery({
    queryKey: ["analysis-history"],
    queryFn: ({ signal }) => getAnalysisHistory(12, signal),
    staleTime: 30_000,
  });
  const openAnalysis = useMutation({
    mutationFn: getSavedAnalysis,
    onSuccess: (saved) => onOpen(saved.analysis),
  });
  const openError = openAnalysis.error;
  const openErrorMessage =
    openError instanceof ApiError && openError.code === "analysis_not_found"
      ? "That saved analysis no longer exists. Refresh the history and try again."
      : "The saved analysis could not be reopened safely.";

  return (
    <section className="panel history-panel" aria-labelledby="history-title">
      <div className="section-heading">
        <div>
          <div className="step-label">Saved locally</div>
          <h2 id="history-title">Recent analysis history</h2>
          <p className="muted">Reopen validated results stored in this local application.</p>
        </div>
        {historyQuery.data && (
          <span className="history-count">
            {historyQuery.data.items.length} saved result
            {historyQuery.data.items.length === 1 ? "" : "s"}
          </span>
        )}
      </div>

      {historyQuery.isPending && (
        <p className="inline-status muted" role="status">
          <span className="spinner spinner-small" aria-hidden="true" />
          Loading saved analyses…
        </p>
      )}
      {historyQuery.isError && (
        <div className="error-card" role="alert">
          <strong>History unavailable</strong>
          <span>The local analysis history could not be loaded.</span>
        </div>
      )}
      {historyQuery.data?.items.length === 0 && (
        <div className="history-empty">
          <strong>No saved analyses yet</strong>
          <span>Complete an automatic or uploaded-PDF analysis and it will appear here.</span>
        </div>
      )}
      {historyQuery.data && historyQuery.data.items.length > 0 && (
        <ul className="history-list" aria-label="Saved analyses">
          {historyQuery.data.items.map((item) => {
            const isOpening = openAnalysis.isPending && openAnalysis.variables === item.id;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  className="history-item"
                  disabled={openAnalysis.isPending}
                  onClick={() => openAnalysis.mutate(item.id)}
                >
                  <span className="history-company">{item.company_name}</span>
                  <strong>{item.announcement_title}</strong>
                  <span className="history-meta">
                    {formatCategory(item.announcement_category)} · Filing {formatDate(item.announcement_published_at)}
                  </span>
                  <span className="history-created">
                    {isOpening ? "Opening…" : `Analyzed ${formatDate(item.created_at, true)}`}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {openError && <p className="error" role="alert">{openErrorMessage}</p>}
    </section>
  );
}
