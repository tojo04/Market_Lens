from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    get_announcement_service,
    get_company_service,
    get_document_service,
)
from app.schemas.domain import AnnouncementListResponse, CompanySearchResponse, ExtractionResult
from app.services.announcement_service import AnnouncementService
from app.services.company_service import CompanyService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/companies", tags=["companies"])
CompanyServiceDependency = Annotated[CompanyService, Depends(get_company_service)]
AnnouncementServiceDependency = Annotated[AnnouncementService, Depends(get_announcement_service)]
DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.get("/search", response_model=CompanySearchResponse)
async def search_companies(
    q: Annotated[str, Query(min_length=1, max_length=100)],
    service: CompanyServiceDependency,
    limit: Annotated[int, Query(ge=1, le=10)] = 10,
) -> CompanySearchResponse:
    return CompanySearchResponse(items=service.search(q, limit))


@router.get("/{company_id}/announcements", response_model=AnnouncementListResponse)
async def list_announcements(
    company_id: str,
    service: AnnouncementServiceDependency,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
) -> AnnouncementListResponse:
    items = await service.list_recent(company_id, from_date, to_date, limit)
    return AnnouncementListResponse(items=items)


@router.post(
    "/{company_id}/announcements/{announcement_id}/extract",
    response_model=ExtractionResult,
)
async def extract_announcement(
    company_id: str,
    announcement_id: str,
    announcement_service: AnnouncementServiceDependency,
    document_service: DocumentServiceDependency,
) -> ExtractionResult:
    return await announcement_service.extract_announcement(
        company_id,
        announcement_id,
        document_service,
    )
