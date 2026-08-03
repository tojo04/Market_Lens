from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Exchange = Literal["BSE", "NSE"]


class DomainModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CompanyMatch(DomainModel):
    provider: NonEmptyString
    company_id: NonEmptyString
    security_code: str | None = None
    symbol: str | None = None
    company_name: NonEmptyString
    exchange: Exchange


class AnnouncementSummary(DomainModel):
    provider: NonEmptyString
    announcement_id: NonEmptyString
    company_id: NonEmptyString
    security_code: str | None = None
    symbol: str | None = None
    company_name: NonEmptyString
    exchange: Exchange
    title: NonEmptyString
    category: str | None = None
    published_at: datetime
    detail_url: str | None = None
    attachment_url: str | None = None
    attachment_type: str | None = None

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("published_at must be timezone-aware")
        return value


class DownloadedAttachment(DomainModel):
    source_url: NonEmptyString
    local_path: Path
    content_type: NonEmptyString
    size_bytes: int = Field(gt=0)


class PageText(DomainModel):
    page_number: int = Field(ge=1)
    text: str


class ExtractionResult(DomainModel):
    status: Literal["success", "scanned_pdf_unsupported"]
    page_count: int = Field(ge=0)
    pages: list[PageText]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def page_count_matches_pages(self) -> Self:
        if self.status == "success" and self.page_count != len(self.pages):
            raise ValueError("page_count must equal the number of extracted pages")
        return self


class DailyClose(DomainModel):
    trading_date: date
    close: float = Field(ge=0, allow_inf_nan=False)


class PriceReaction(DomainModel):
    previous_trading_date: date | None = None
    previous_close: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    next_trading_date: date | None = None
    next_close: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    percentage_change: float | None = Field(default=None, allow_inf_nan=False)
    status: Literal["available", "unavailable"]
    note: str | None = None

    @model_validator(mode="after")
    def available_values_are_complete(self) -> Self:
        values = (
            self.previous_trading_date,
            self.previous_close,
            self.next_trading_date,
            self.next_close,
            self.percentage_change,
        )
        if self.status == "available" and any(value is None for value in values):
            raise ValueError("available price reactions require all price fields")
        if self.status == "unavailable" and self.percentage_change is not None:
            raise ValueError("unavailable price reactions cannot contain a percentage change")
        return self


class CompanySearchResponse(DomainModel):
    items: list[CompanyMatch]


class AnnouncementListResponse(DomainModel):
    items: list[AnnouncementSummary]
