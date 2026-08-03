import { apiRequest } from "./client";
import type { ExtractionResult } from "../types/market";

export function extractAnnouncement(
  companyId: string,
  announcementId: string,
): Promise<ExtractionResult> {
  return apiRequest<ExtractionResult>(
    `/companies/${encodeURIComponent(companyId)}/announcements/${encodeURIComponent(announcementId)}/extract`,
    { method: "POST" },
  );
}

export function extractUpload(file: File): Promise<ExtractionResult> {
  const body = new FormData();
  body.append("file", file);
  return apiRequest<ExtractionResult>("/documents/extract-upload", {
    method: "POST",
    body,
  });
}

