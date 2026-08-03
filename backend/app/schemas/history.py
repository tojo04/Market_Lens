from datetime import datetime

from pydantic import Field

from app.schemas.analysis import AnnouncementAnalysis, AnnouncementCategory
from app.schemas.domain import DomainModel, Exchange


class AnalysisHistoryItem(DomainModel):
    id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    exchange: Exchange
    symbol: str | None
    security_code: str | None
    announcement_title: str = Field(min_length=1)
    announcement_category: AnnouncementCategory
    announcement_published_at: datetime | None
    created_at: datetime


class AnalysisHistoryResponse(DomainModel):
    items: list[AnalysisHistoryItem]


class StoredAnalysisResponse(DomainModel):
    id: str = Field(min_length=1)
    created_at: datetime
    analysis: AnnouncementAnalysis
