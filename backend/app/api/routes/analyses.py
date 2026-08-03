from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies import get_analysis_service
from app.schemas.analysis import AnalyzeAnnouncementRequest, AnnouncementAnalysis
from app.schemas.domain import Exchange
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analyses", tags=["analyses"])
AnalysisServiceDependency = Annotated[AnalysisService, Depends(get_analysis_service)]


@router.post("/from-announcement", response_model=AnnouncementAnalysis)
async def analyze_selected_announcement(
    request: AnalyzeAnnouncementRequest,
    service: AnalysisServiceDependency,
) -> AnnouncementAnalysis:
    return await service.analyze_announcement(request)


@router.post("/from-upload", response_model=AnnouncementAnalysis)
async def analyze_uploaded_announcement(
    service: AnalysisServiceDependency,
    file: Annotated[UploadFile, File(description="Official BSE/NSE announcement PDF")],
    symbol: Annotated[str, Form(min_length=1, max_length=30)],
    exchange: Annotated[Exchange, Form()],
    announcement_date: Annotated[date, Form()],
    company_name: Annotated[str | None, Form(max_length=200)] = None,
    security_code: Annotated[str | None, Form(max_length=20)] = None,
) -> AnnouncementAnalysis:
    return await service.analyze_upload(
        upload=file,
        symbol=symbol,
        exchange=exchange,
        announcement_date=announcement_date,
        company_name=company_name,
        security_code=security_code,
    )
