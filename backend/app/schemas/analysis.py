import re
from datetime import date, datetime
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from app.schemas.domain import DomainModel, Exchange, PageText, PriceReaction

REQUIRED_DISCLAIMER = (
    "This is an educational explanation of public information, not investment advice."
)
AnnouncementCategory = Literal[
    "financial_results",
    "dividend",
    "order_or_contract",
    "acquisition_or_investment",
    "management_change",
    "fundraising",
    "corporate_action",
    "other",
]
SUPPORTED_CATEGORIES = {
    "financial_results",
    "dividend",
    "order_or_contract",
    "acquisition_or_investment",
    "management_change",
    "fundraising",
    "corporate_action",
    "other",
}
PROHIBITED_RECOMMENDATIONS = re.compile(
    r"\b(?:recommend(?:s|ed|ation)?\s+)?(?:buy|sell|hold)\s+(?:the\s+)?(?:stock|shares?)\b"
    r"|\btarget\s+price\b|\bstop[- ]loss\b",
    re.IGNORECASE,
)


class ImportantFact(DomainModel):
    label: str = Field(min_length=1)
    value: str = Field(min_length=1)
    source_excerpt: str | None = None
    page_number: int | None = Field(default=None, ge=1)


class SourceMetadata(DomainModel):
    provider: str = Field(min_length=1)
    exchange: Exchange
    company_name: str = Field(min_length=1)
    symbol: str | None = None
    security_code: str | None = None
    announcement_id: str | None = None
    announcement_url: str | None = None
    attachment_url: str | None = None
    published_at: datetime | None = None


class AnnouncementAnalysis(DomainModel):
    announcement_category: AnnouncementCategory
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    important_facts: list[ImportantFact]
    why_it_matters: list[str]
    positive_signals: list[str]
    risks: list[str]
    price_reaction: PriceReaction
    confidence: Literal["low", "medium", "high"]
    limitations: list[str]
    source: SourceMetadata
    disclaimer: Literal[
        "This is an educational explanation of public information, not investment advice."
    ]

    @field_validator("announcement_category", mode="before")
    @classmethod
    def normalize_unknown_category(cls, value: object) -> object:
        if isinstance(value, str) and value not in SUPPORTED_CATEGORIES:
            return "other"
        return value

    @model_validator(mode="after")
    def reject_trade_recommendations(self) -> Self:
        user_facing_text = "\n".join(
            [
                self.title,
                self.summary,
                *self.why_it_matters,
                *self.positive_signals,
                *self.risks,
                *self.limitations,
            ]
        )
        if PROHIBITED_RECOMMENDATIONS.search(user_facing_text):
            raise ValueError("analysis contains prohibited trade-recommendation language")
        return self


class AnalysisInput(DomainModel):
    source: SourceMetadata
    pages: list[PageText]
    extraction_warnings: list[str] = Field(default_factory=list)
    announcement_date: date


class GetPriceReactionArguments(DomainModel):
    symbol: str | None
    exchange: Exchange
    announcement_date: date


class AnalyzeAnnouncementRequest(DomainModel):
    provider: Literal["bse"]
    company_id: str = Field(min_length=1)
    announcement_id: str = Field(min_length=1)
