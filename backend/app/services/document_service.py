import asyncio
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import FileTooLargeError, InvalidDocumentError
from app.schemas.domain import ExtractionResult
from app.services.attachment_service import ALLOWED_PDF_CONTENT_TYPES, AttachmentService
from app.services.pdf_service import PdfService


class DocumentService:
    def __init__(
        self,
        settings: Settings,
        attachment_service: AttachmentService,
        pdf_service: PdfService,
        temp_directory: Path | None = None,
    ) -> None:
        self._settings = settings
        self._attachment_service = attachment_service
        self._pdf_service = pdf_service
        self._temp_directory = temp_directory

    async def extract_remote(self, source_url: str) -> ExtractionResult:
        attachment = await self._attachment_service.download_pdf(source_url)
        try:
            return await asyncio.to_thread(
                self._pdf_service.extract_pdf_text,
                attachment.local_path,
            )
        finally:
            self._attachment_service.cleanup(attachment)

    async def extract_upload(self, upload: UploadFile) -> ExtractionResult:
        content_type = (upload.content_type or "").split(";", 1)[0].casefold()
        if content_type not in ALLOWED_PDF_CONTENT_TYPES:
            raise InvalidDocumentError("Uploaded file must be a PDF")
        path: Path | None = None
        size = 0
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".pdf",
                prefix="marketlens-upload-",
                dir=self._temp_directory,
                delete=False,
            ) as temporary:
                path = Path(temporary.name)
                while chunk := await upload.read(64 * 1024):
                    size += len(chunk)
                    if size > self._settings.max_download_bytes:
                        raise FileTooLargeError("Uploaded PDF exceeds the maximum allowed size")
                    temporary.write(chunk)
            if size == 0:
                raise InvalidDocumentError("Uploaded PDF is empty")
            assert path is not None
            return await asyncio.to_thread(self._pdf_service.extract_pdf_text, path)
        finally:
            if path is not None:
                path.unlink(missing_ok=True)
