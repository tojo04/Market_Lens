from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AnnouncementNotFoundError,
    AttachmentUnavailableError,
    CompanyNotFoundError,
    FileTooLargeError,
    InvalidDocumentError,
    MarketLensError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    ScannedPdfUnsupportedError,
    UnsafeDownloadError,
)

STATUS_BY_ERROR = {
    CompanyNotFoundError: 404,
    AnnouncementNotFoundError: 404,
    AttachmentUnavailableError: 404,
    ProviderUnavailableError: 503,
    ProviderRateLimitError: 429,
    UnsafeDownloadError: 400,
    FileTooLargeError: 413,
    ScannedPdfUnsupportedError: 422,
    InvalidDocumentError: 422,
}


async def marketlens_error_handler(request: Request, error: MarketLensError) -> JSONResponse:
    status_code = next(
        (status for error_type, status in STATUS_BY_ERROR.items() if isinstance(error, error_type)),
        400,
    )
    content: dict[str, Any] = {
        "error": {
            "code": error.code,
            "message": error.message,
            "request_id": getattr(request.state, "request_id", None),
            "fallback_available": isinstance(error, ProviderUnavailableError),
        }
    }
    if isinstance(error, ProviderRateLimitError):
        content["error"]["retry_after_seconds"] = error.retry_after_seconds
    return JSONResponse(status_code=status_code, content=content)
