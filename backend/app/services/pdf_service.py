from pathlib import Path

import fitz

from app.core.config import Settings
from app.core.exceptions import FileTooLargeError, InvalidDocumentError
from app.schemas.domain import ExtractionResult, PageText


class PdfService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract_pdf_text(self, path: Path) -> ExtractionResult:
        try:
            size = path.stat().st_size
        except OSError as error:
            raise InvalidDocumentError("PDF file is unavailable") from error
        if size == 0:
            raise InvalidDocumentError("PDF file is empty")
        if size > self._settings.max_download_bytes:
            raise FileTooLargeError("PDF exceeds the maximum allowed size")
        try:
            with path.open("rb") as pdf_file:
                if pdf_file.read(5) != b"%PDF-":
                    raise InvalidDocumentError("File signature is not PDF")
        except OSError as error:
            raise InvalidDocumentError("PDF could not be read") from error

        try:
            document = fitz.open(path)
        except (fitz.FileDataError, RuntimeError) as error:
            raise InvalidDocumentError("PDF structure is invalid") from error
        try:
            page_count = document.page_count
            if page_count == 0:
                raise InvalidDocumentError("PDF contains no pages")
            if page_count > self._settings.max_pdf_pages:
                raise InvalidDocumentError("PDF exceeds the maximum page count")
            pages: list[PageText] = []
            warnings: list[str] = []
            has_text = False
            for index, page in enumerate(document, start=1):
                text = page.get_text("text", sort=True).strip()
                if text:
                    has_text = True
                else:
                    warnings.append(f"Page {index} contains no extractable text")
                pages.append(PageText(page_number=index, text=text))
            if not has_text:
                return ExtractionResult(
                    status="scanned_pdf_unsupported",
                    page_count=page_count,
                    pages=[],
                    warnings=["No extractable text was found; OCR is not supported in the MVP"],
                )
            return ExtractionResult(
                status="success",
                page_count=page_count,
                pages=pages,
                warnings=warnings,
            )
        finally:
            document.close()
