export type Exchange = "BSE" | "NSE";

export interface CompanyMatch {
  provider: string;
  company_id: string;
  security_code: string | null;
  symbol: string | null;
  company_name: string;
  exchange: Exchange;
}

export interface CompanySearchResponse {
  items: CompanyMatch[];
}

export interface AnnouncementSummary {
  provider: string;
  announcement_id: string;
  company_id: string;
  security_code: string | null;
  symbol: string | null;
  company_name: string;
  exchange: Exchange;
  title: string;
  category: string | null;
  published_at: string;
  detail_url: string | null;
  attachment_url: string | null;
  attachment_type: string | null;
}

export interface AnnouncementListResponse {
  items: AnnouncementSummary[];
}

export interface PageText {
  page_number: number;
  text: string;
}

export interface ExtractionResult {
  status: "success" | "scanned_pdf_unsupported";
  page_count: number;
  pages: PageText[];
  warnings: string[];
}
