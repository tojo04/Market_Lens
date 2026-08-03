from datetime import date, datetime, time, timedelta, timezone

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.agents.announcement_agent import AnnouncementAgent
from app.core.exceptions import AttachmentUnavailableError, ScannedPdfUnsupportedError
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import (
    AnalysisInput,
    AnalyzeAnnouncementRequest,
    AnnouncementAnalysis,
    SourceMetadata,
)
from app.schemas.domain import Exchange, ExtractionResult
from app.services.announcement_service import AnnouncementService
from app.services.company_service import CompanyService
from app.services.document_service import DocumentService

INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


class AnalysisService:
    def __init__(
        self,
        company_service: CompanyService,
        announcement_service: AnnouncementService,
        document_service: DocumentService,
        agent: AnnouncementAgent,
        analysis_repository: AnalysisRepository,
    ) -> None:
        self._company_service = company_service
        self._announcement_service = announcement_service
        self._document_service = document_service
        self._agent = agent
        self._analysis_repository = analysis_repository

    async def analyze_announcement(
        self,
        request: AnalyzeAnnouncementRequest,
    ) -> AnnouncementAnalysis:
        self._company_service.get_by_id(request.company_id)
        announcement = await self._announcement_service.resolve_announcement(
            request.company_id,
            request.announcement_id,
        )
        if not announcement.attachment_url:
            raise AttachmentUnavailableError("Selected announcement has no PDF attachment")
        extraction = await self._document_service.extract_remote(announcement.attachment_url)
        _require_text_extraction(extraction)
        source = SourceMetadata(
            provider=announcement.provider,
            exchange=announcement.exchange,
            company_name=announcement.company_name,
            symbol=announcement.symbol,
            security_code=announcement.security_code,
            announcement_id=announcement.announcement_id,
            announcement_url=announcement.detail_url,
            attachment_url=announcement.attachment_url,
            published_at=announcement.published_at,
        )
        analysis = await self._agent.analyze(
            AnalysisInput(
                source=source,
                pages=extraction.pages,
                extraction_warnings=extraction.warnings,
                announcement_date=announcement.published_at.date(),
            )
        )
        await run_in_threadpool(self._analysis_repository.save, analysis)
        return analysis

    async def analyze_upload(
        self,
        *,
        upload: UploadFile,
        symbol: str,
        exchange: Exchange,
        announcement_date: date,
        company_name: str | None,
        security_code: str | None,
    ) -> AnnouncementAnalysis:
        extraction = await self._document_service.extract_upload(upload)
        _require_text_extraction(extraction)
        source = SourceMetadata(
            provider="manual_upload",
            exchange=exchange,
            company_name=(company_name or symbol or security_code or "Uploaded announcement"),
            symbol=symbol or None,
            security_code=security_code,
            announcement_id=None,
            announcement_url=None,
            attachment_url=None,
            published_at=datetime.combine(announcement_date, time.min, tzinfo=INDIA_TIMEZONE),
        )
        analysis = await self._agent.analyze(
            AnalysisInput(
                source=source,
                pages=extraction.pages,
                extraction_warnings=extraction.warnings,
                announcement_date=announcement_date,
            )
        )
        await run_in_threadpool(self._analysis_repository.save, analysis)
        return analysis


def _require_text_extraction(extraction: ExtractionResult) -> None:
    if extraction.status == "scanned_pdf_unsupported":
        raise ScannedPdfUnsupportedError("Scanned or image-only PDFs require unsupported OCR")
