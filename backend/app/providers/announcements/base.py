from datetime import date
from typing import Protocol, runtime_checkable

from app.schemas.domain import AnnouncementSummary, CompanyMatch, DownloadedAttachment


@runtime_checkable
class AnnouncementProvider(Protocol):
    async def search_companies(self, query: str, limit: int = 10) -> list[CompanyMatch]: ...

    async def get_recent_announcements(
        self,
        company_id: str,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 20,
    ) -> list[AnnouncementSummary]: ...

    async def download_attachment(self, announcement_id: str) -> DownloadedAttachment: ...
