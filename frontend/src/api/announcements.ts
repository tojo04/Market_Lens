import { apiRequest } from "./client";
import type { AnnouncementListResponse } from "../types/market";

export function getRecentAnnouncements(
  companyId: string,
  signal?: AbortSignal,
): Promise<AnnouncementListResponse> {
  return apiRequest<AnnouncementListResponse>(
    `/companies/${encodeURIComponent(companyId)}/announcements?limit=20`,
    { signal },
  );
}

