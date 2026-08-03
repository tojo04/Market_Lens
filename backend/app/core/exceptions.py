class MarketLensError(Exception):
    """Base class for controlled domain failures."""

    code = "marketlens_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ProviderUnavailableError(MarketLensError):
    code = "provider_unavailable"


class ProviderRateLimitError(MarketLensError):
    code = "provider_rate_limited"

    def __init__(self, message: str, retry_after_seconds: int | None = None) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


class CompanyNotFoundError(MarketLensError):
    code = "company_not_found"


class AmbiguousCompanyError(MarketLensError):
    code = "ambiguous_company"


class AnnouncementNotFoundError(MarketLensError):
    code = "announcement_not_found"


class AttachmentUnavailableError(MarketLensError):
    code = "attachment_unavailable"


class UnsafeDownloadError(MarketLensError):
    code = "unsafe_attachment_url"


class InvalidDocumentError(MarketLensError):
    code = "invalid_pdf"


class FileTooLargeError(InvalidDocumentError):
    code = "file_too_large"


class ScannedPdfUnsupportedError(InvalidDocumentError):
    code = "scanned_pdf_unsupported"


class MarketDataUnavailableError(MarketLensError):
    code = "market_data_unavailable"


class AnalysisProviderError(MarketLensError):
    code = "analysis_provider_error"


class AnalysisValidationError(MarketLensError):
    code = "analysis_validation_error"
