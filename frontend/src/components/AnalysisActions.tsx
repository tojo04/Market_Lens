import { useMutation } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { analyzeAnnouncement, analyzeUpload } from "../api/analyses";
import { ApiError } from "../api/client";
import type {
  AnnouncementAnalysis,
  AnnouncementSummary,
  CompanyMatch,
  Exchange,
} from "../types/market";

interface AnalysisActionsProps {
  company: CompanyMatch | null;
  announcement: AnnouncementSummary | null;
  onComplete: (analysis: AnnouncementAnalysis) => void;
}

const ACTIVITY_STAGES = [
  "Finding announcements",
  "Downloading official attachment",
  "Extracting document",
  "Analyzing facts",
  "Checking nearby prices",
  "Preparing result",
] as const;

const ERROR_MESSAGES: Record<string, string> = {
  company_not_found: "That company is no longer available. Search and select it again.",
  announcement_not_found: "That announcement is no longer in the recent results.",
  provider_unavailable:
    "BSE retrieval is temporarily unavailable. Upload the official PDF below to continue.",
  provider_rate_limited:
    "BSE is temporarily rate-limiting requests. Try again later or upload the official PDF.",
  attachment_unavailable: "This announcement does not include an available PDF attachment.",
  unsafe_attachment_url: "The attachment did not pass the application’s security checks.",
  file_too_large: "The PDF exceeds the configured file-size limit.",
  invalid_pdf: "The selected file is not a valid text PDF.",
  scanned_pdf_unsupported: "This PDF appears scanned. OCR is not supported in the MVP.",
  market_data_unavailable: "Nearby market prices are temporarily unavailable.",
  analysis_provider_error: "The analysis provider is unavailable. Please try again shortly.",
  analysis_validation_error: "The analysis could not be validated safely. Please try again.",
};

function ActivityProgress({ mode }: { mode: "automatic" | "upload" }) {
  const [currentStage, setCurrentStage] = useState(mode === "automatic" ? 1 : 2);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCurrentStage((stage) => Math.min(stage + 1, ACTIVITY_STAGES.length - 1));
    }, 1400);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="activity" role="status" aria-live="polite">
      <div className="activity-heading">
        <span className="spinner" aria-hidden="true" />
        <strong>Preparing a grounded explanation</strong>
      </div>
      <ol className="activity-list">
        {ACTIVITY_STAGES.map((stage, index) => (
          <li
            key={stage}
            className={
              index < currentStage ? "activity-done" : index === currentStage ? "activity-current" : ""
            }
          >
            {stage}
          </li>
        ))}
      </ol>
    </div>
  );
}

function AnalysisError({ error }: { error: Error }) {
  const apiError = error instanceof ApiError ? error : null;
  const message = apiError
    ? (ERROR_MESSAGES[apiError.code] ?? apiError.message)
    : "The request could not be completed. Please try again.";

  return (
    <div className="error-card" role="alert">
      <strong>Analysis not completed</strong>
      <span>{message}</span>
      {apiError?.requestId && <small>Request ID: {apiError.requestId}</small>}
    </div>
  );
}

export function AnalysisActions({ company, announcement, onComplete }: AnalysisActionsProps) {
  const [file, setFile] = useState<File | null>(null);
  const automaticAnalysis = useMutation({
    mutationFn: analyzeAnnouncement,
    onSuccess: onComplete,
  });
  const uploadAnalysis = useMutation({
    mutationFn: analyzeUpload,
    onSuccess: onComplete,
  });
  const mode = automaticAnalysis.isPending
    ? "automatic"
    : uploadAnalysis.isPending
      ? "upload"
      : null;
  const isBusy = mode !== null;
  const failure = automaticAnalysis.error ?? uploadAnalysis.error;
  const defaultDate = announcement?.published_at.slice(0, 10) ?? "";

  const startAutomaticAnalysis = () => {
    if (!company || !announcement || announcement.provider !== "bse") return;
    uploadAnalysis.reset();
    automaticAnalysis.mutate({
      provider: "bse",
      company_id: company.company_id,
      announcement_id: announcement.announcement_id,
    });
  };

  const submitUpload = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;
    const formData = new FormData(event.currentTarget);
    const exchangeValue = String(formData.get("exchange"));
    const exchange: Exchange = exchangeValue === "NSE" ? "NSE" : "BSE";
    automaticAnalysis.reset();
    uploadAnalysis.mutate({
      file,
      symbol: String(formData.get("symbol") ?? "").trim(),
      exchange,
      announcementDate: String(formData.get("announcement_date") ?? ""),
      companyName: String(formData.get("company_name") ?? "").trim() || undefined,
      securityCode: String(formData.get("security_code") ?? "").trim() || undefined,
    });
  };

  return (
    <section className="panel actions-panel" aria-labelledby="analysis-action-title">
      <div className="section-heading">
        <div>
          <div className="step-label">Step 3</div>
          <h2 id="analysis-action-title">Analyze one official filing</h2>
          <p className="muted">
            MarketLens extracts the selected PDF, explains its facts, and checks nearby prices.
          </p>
        </div>
        <span className="safety-label">One filing · One agent · No trade advice</span>
      </div>

      <div className="automatic-action">
        <div>
          <strong>{announcement?.title ?? "Select an announcement above"}</strong>
          <span>
            {announcement?.attachment_url
              ? "Official PDF attachment is available."
              : "A PDF attachment is required for automatic analysis."}
          </span>
        </div>
        <button
          type="button"
          className="primary-button"
          disabled={
            !company ||
            !announcement?.attachment_url ||
            announcement.provider !== "bse" ||
            isBusy
          }
          onClick={startAutomaticAnalysis}
        >
          {automaticAnalysis.isPending ? "Analyzing selected filing…" : "Analyze announcement"}
        </button>
      </div>

      {mode && <ActivityProgress mode={mode} />}
      {failure && !isBusy && <AnalysisError error={failure} />}

      <details className="upload-fallback" open={!announcement ? true : undefined}>
        <summary>Upload official announcement PDF instead</summary>
        <p className="muted">
          Use this fallback if exchange retrieval fails. The PDF is processed temporarily and is
          not retained.
        </p>
        <form className="upload-form" onSubmit={submitUpload}>
          <div className="form-field form-field-wide">
            <label htmlFor="pdf-upload">Official PDF</label>
            <input
              id="pdf-upload"
              name="file"
              type="file"
              accept="application/pdf,.pdf"
              required
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="upload-symbol">Symbol or security code</label>
            <input
              id="upload-symbol"
              name="symbol"
              defaultValue={company?.symbol ?? company?.security_code ?? ""}
              placeholder="INFY or 500209"
              maxLength={30}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="upload-exchange">Exchange</label>
            <select id="upload-exchange" name="exchange" defaultValue={company?.exchange ?? "BSE"}>
              <option value="BSE">BSE</option>
              <option value="NSE">NSE</option>
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="announcement-date">Announcement date</label>
            <input
              id="announcement-date"
              name="announcement_date"
              type="date"
              defaultValue={defaultDate}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="upload-company">Company name</label>
            <input
              id="upload-company"
              name="company_name"
              defaultValue={company?.company_name ?? ""}
              maxLength={200}
              placeholder="Optional"
            />
          </div>
          <div className="form-field">
            <label htmlFor="security-code">BSE security code</label>
            <input
              id="security-code"
              name="security_code"
              defaultValue={company?.security_code ?? ""}
              maxLength={20}
              inputMode="numeric"
              placeholder="Optional"
            />
          </div>
          <button type="submit" className="secondary-button form-submit" disabled={!file || isBusy}>
            {uploadAnalysis.isPending ? "Analyzing uploaded filing…" : "Analyze uploaded PDF"}
          </button>
        </form>
      </details>
    </section>
  );
}
