from datetime import date

from app.core.exceptions import AnnouncementNotFoundError, AttachmentUnavailableError
from app.providers.announcements.base import AnnouncementProvider
from app.schemas.domain import AnnouncementSummary, ExtractionResult
from app.services.company_service import CompanyService
from app.services.document_service import DocumentService


class AnnouncementService:
    def __init__(
        self,
        provider: AnnouncementProvider,
        company_service: CompanyService,
    ) -> None:
        self._provider = provider
        self._company_service = company_service

    async def list_recent(
        self,
        company_id: str,
        from_date: date | None,
        to_date: date | None,
        limit: int,
    ) -> list[AnnouncementSummary]:
        self._company_service.get_by_id(company_id)
        return await self._provider.get_recent_announcements(
            company_id=company_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )

    async def extract_announcement(
        self,
        company_id: str,
        announcement_id: str,
        document_service: DocumentService,
    ) -> ExtractionResult:
        announcements = await self.list_recent(company_id, None, None, 20)
        announcement = next(
            (item for item in announcements if item.announcement_id == announcement_id),
            None,
        )
        if announcement is None:
            raise AnnouncementNotFoundError("Selected announcement was not found")
        if not announcement.attachment_url:
            raise AttachmentUnavailableError("Selected announcement has no PDF attachment")
        return await document_service.extract_remote(announcement.attachment_url)
