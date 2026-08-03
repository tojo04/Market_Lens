from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.providers.announcements.base import AnnouncementProvider
from app.providers.market_data.base import MarketDataProvider
from app.schemas.domain import (
    AnnouncementSummary,
    CompanyMatch,
    DailyClose,
    DownloadedAttachment,
    ExtractionResult,
    PageText,
    PriceReaction,
)


class CompleteProvider:
    async def search_companies(self, query: str, limit: int = 10) -> list[CompanyMatch]:
        return []

    async def get_recent_announcements(
        self, *args: object, **kwargs: object
    ) -> list[AnnouncementSummary]:
        return []

    async def download_attachment(self, announcement_id: str) -> DownloadedAttachment:
        raise NotImplementedError

    async def get_daily_closes(self, *args: object, **kwargs: object) -> list[DailyClose]:
        return []


def test_normalized_models_accept_valid_values() -> None:
    company = CompanyMatch(
        provider="local",
        company_id="500209",
        security_code="500209",
        symbol="INFY",
        company_name="Infosys Limited",
        exchange="BSE",
    )
    announcement = AnnouncementSummary(
        provider="bse",
        announcement_id="news-1",
        company_id=company.company_id,
        security_code=company.security_code,
        symbol=company.symbol,
        company_name=company.company_name,
        exchange="BSE",
        title="Board meeting outcome",
        published_at=datetime(2026, 8, 3, 10, 30, tzinfo=UTC),
    )
    extraction = ExtractionResult(
        status="success",
        page_count=1,
        pages=[PageText(page_number=1, text="Announcement text")],
    )
    close = DailyClose(trading_date=date(2026, 8, 3), close=1500.25)

    assert announcement.security_code == "500209"
    assert extraction.page_count == 1
    assert close.close == 1500.25


def test_announcement_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        AnnouncementSummary(
            provider="bse",
            announcement_id="news-1",
            company_id="500209",
            company_name="Infosys Limited",
            exchange="BSE",
            title="Outcome",
            published_at=datetime(2026, 8, 3, 10, 30),
        )


def test_extraction_page_count_must_match_pages() -> None:
    with pytest.raises(ValidationError, match="page_count"):
        ExtractionResult(
            status="success",
            page_count=2,
            pages=[PageText(page_number=1, text="Only page")],
        )


def test_available_price_reaction_requires_complete_values() -> None:
    with pytest.raises(ValidationError, match="all price fields"):
        PriceReaction(status="available")


def test_downloaded_attachment_is_internal_path_metadata() -> None:
    attachment = DownloadedAttachment(
        source_url="https://www.bseindia.com/example.pdf",
        local_path=Path("example.pdf"),
        content_type="application/pdf",
        size_bytes=100,
    )

    assert attachment.size_bytes == 100


def test_provider_protocols_are_runtime_checkable() -> None:
    provider = CompleteProvider()

    assert isinstance(provider, AnnouncementProvider)
    assert isinstance(provider, MarketDataProvider)
