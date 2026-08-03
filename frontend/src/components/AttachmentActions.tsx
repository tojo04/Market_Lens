import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError } from "../api/client";
import { extractAnnouncement, extractUpload } from "../api/documents";
import type { AnnouncementSummary, CompanyMatch, ExtractionResult } from "../types/market";

interface AttachmentActionsProps {
  company: CompanyMatch | null;
  announcement: AnnouncementSummary | null;
}

function errorMessage(error: Error): string {
  if (!(error instanceof ApiError)) return "Document processing failed. Please try again.";
  const messages: Record<string, string> = {
    attachment_unavailable: "This announcement does not have an available PDF attachment.",
    file_too_large: "The PDF exceeds the configured size limit.",
    invalid_pdf: "The selected file is not a valid text PDF.",
    scanned_pdf_unsupported: "This scanned PDF needs OCR, which is not supported yet.",
    unsafe_attachment_url: "The attachment URL did not pass the security checks.",
  };
  return messages[error.code] ?? error.message;
}

function ExtractionStatus({ result }: { result: ExtractionResult }) {
  if (result.status === "scanned_pdf_unsupported") {
    return <p className="error">The PDF appears scanned or image-only. OCR is not supported yet.</p>;
  }
  return (
    <div className="ready-state" role="status">
      <strong>Document extracted safely</strong>
      <span>{result.page_count} page{result.page_count === 1 ? "" : "s"} ready for analysis.</span>
      {result.warnings.map((warning) => <small key={warning}>{warning}</small>)}
    </div>
  );
}

export function AttachmentActions({ company, announcement }: AttachmentActionsProps) {
  const [file, setFile] = useState<File | null>(null);
  const remoteExtraction = useMutation({
    mutationFn: () => {
      if (!company || !announcement) throw new Error("Select an announcement first");
      return extractAnnouncement(company.company_id, announcement.announcement_id);
    },
  });
  const uploadExtraction = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Choose a PDF first");
      return extractUpload(file);
    },
  });
  const result = remoteExtraction.data ?? uploadExtraction.data;
  const failure = remoteExtraction.error ?? uploadExtraction.error;

  return (
    <section className="panel actions-panel" aria-labelledby="document-title">
      <div className="step-label">Step 3</div>
      <h2 id="document-title">Prepare the official document</h2>
      <button
        type="button"
        className="primary-button"
        disabled={!announcement?.attachment_url || remoteExtraction.isPending}
        onClick={() => remoteExtraction.mutate()}
      >
        {remoteExtraction.isPending ? "Downloading and extracting…" : "Analyze selected announcement"}
      </button>

      <div className="divider" aria-hidden="true">or</div>
      <label htmlFor="pdf-upload">Upload official announcement PDF instead</label>
      <input
        id="pdf-upload"
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
      <button
        type="button"
        className="secondary-button"
        disabled={!file || uploadExtraction.isPending}
        onClick={() => uploadExtraction.mutate()}
      >
        {uploadExtraction.isPending ? "Extracting uploaded PDF…" : "Use uploaded PDF"}
      </button>

      {failure && <p className="error" role="alert">{errorMessage(failure)}</p>}
      {result && <ExtractionStatus result={result} />}
    </section>
  );
}

