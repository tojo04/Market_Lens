from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import get_document_service
from app.schemas.domain import ExtractionResult
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.post("/extract-upload", response_model=ExtractionResult)
async def extract_uploaded_pdf(
    service: DocumentServiceDependency,
    file: Annotated[UploadFile, File(description="Official BSE/NSE announcement PDF")],
) -> ExtractionResult:
    return await service.extract_upload(file)
