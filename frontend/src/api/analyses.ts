import { apiRequest } from "./client";
import type {
  AnalyzeAnnouncementRequest,
  AnalyzeUploadRequest,
  AnnouncementAnalysis,
  AnalysisHistoryResponse,
  StoredAnalysisResponse,
} from "../types/market";

export function analyzeAnnouncement(
  request: AnalyzeAnnouncementRequest,
): Promise<AnnouncementAnalysis> {
  return apiRequest<AnnouncementAnalysis>("/analyses/from-announcement", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function analyzeUpload(request: AnalyzeUploadRequest): Promise<AnnouncementAnalysis> {
  const body = new FormData();
  body.append("file", request.file);
  body.append("symbol", request.symbol);
  body.append("exchange", request.exchange);
  body.append("announcement_date", request.announcementDate);
  if (request.companyName) body.append("company_name", request.companyName);
  if (request.securityCode) body.append("security_code", request.securityCode);

  return apiRequest<AnnouncementAnalysis>("/analyses/from-upload", {
    method: "POST",
    body,
  });
}

export function getAnalysisHistory(
  limit = 12,
  signal?: AbortSignal,
): Promise<AnalysisHistoryResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest<AnalysisHistoryResponse>(`/analyses?${params.toString()}`, { signal });
}

export function getSavedAnalysis(analysisId: string): Promise<StoredAnalysisResponse> {
  return apiRequest<StoredAnalysisResponse>(`/analyses/${encodeURIComponent(analysisId)}`);
}
