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

export interface ImportantFact {
  label: string;
  value: string;
  source_excerpt: string | null;
  page_number: number | null;
}

export interface PriceReaction {
  previous_trading_date: string | null;
  previous_close: number | null;
  next_trading_date: string | null;
  next_close: number | null;
  percentage_change: number | null;
  status: "available" | "unavailable";
  note: string | null;
}

export interface SourceMetadata {
  provider: string;
  exchange: Exchange;
  company_name: string;
  symbol: string | null;
  security_code: string | null;
  announcement_id: string | null;
  announcement_url: string | null;
  attachment_url: string | null;
  published_at: string | null;
}

export type AnnouncementCategory =
  | "financial_results"
  | "dividend"
  | "order_or_contract"
  | "acquisition_or_investment"
  | "management_change"
  | "fundraising"
  | "corporate_action"
  | "other";

export interface AnnouncementAnalysis {
  announcement_category: AnnouncementCategory;
  title: string;
  summary: string;
  important_facts: ImportantFact[];
  why_it_matters: string[];
  positive_signals: string[];
  risks: string[];
  price_reaction: PriceReaction;
  confidence: "low" | "medium" | "high";
  limitations: string[];
  source: SourceMetadata;
  disclaimer: string;
}

export interface AnalyzeAnnouncementRequest {
  provider: "bse";
  company_id: string;
  announcement_id: string;
}

export interface AnalyzeUploadRequest {
  file: File;
  symbol: string;
  exchange: Exchange;
  announcementDate: string;
  companyName?: string;
  securityCode?: string;
}
