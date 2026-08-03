import { apiRequest } from "./client";
import type { CompanySearchResponse } from "../types/market";

export function searchCompanies(query: string, signal?: AbortSignal): Promise<CompanySearchResponse> {
  const params = new URLSearchParams({ q: query, limit: "10" });
  return apiRequest<CompanySearchResponse>(`/companies/search?${params.toString()}`, { signal });
}

