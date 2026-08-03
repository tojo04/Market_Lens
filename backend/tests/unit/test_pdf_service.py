from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.exceptions import InvalidDocumentError
from app.services.pdf_service import PdfService
from tests.helpers import make_pdf_bytes


def write_fixture(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def test_valid_text_pdf_is_page_aware(tmp_path: Path) -> None:
    path = write_fixture(tmp_path / "valid.pdf", make_pdf_bytes(["First page", "Second page"]))
    result = PdfService(Settings(environment="test")).extract_pdf_text(path)

    assert result.status == "success"
    assert result.page_count == 2
    assert result.pages[0].page_number == 1
    assert "First page" in result.pages[0].text


@pytest.mark.parametrize("content", [b"", b"not a pdf", b"%PDF-invalid"])
def test_empty_and_invalid_pdf_is_rejected(tmp_path: Path, content: bytes) -> None:
    path = write_fixture(tmp_path / "invalid.pdf", content)

    with pytest.raises(InvalidDocumentError):
        PdfService(Settings(environment="test")).extract_pdf_text(path)


def test_image_only_pdf_returns_scanned_status(tmp_path: Path) -> None:
    path = write_fixture(tmp_path / "scanned.pdf", make_pdf_bytes([""]))
    result = PdfService(Settings(environment="test")).extract_pdf_text(path)

    assert result.status == "scanned_pdf_unsupported"
    assert result.pages == []


def test_page_limit_is_enforced(tmp_path: Path) -> None:
    path = write_fixture(tmp_path / "long.pdf", make_pdf_bytes(["one", "two"]))

    with pytest.raises(InvalidDocumentError, match="page count"):
        PdfService(Settings(environment="test", max_pdf_pages=1)).extract_pdf_text(path)


def test_blank_page_produces_warning(tmp_path: Path) -> None:
    path = write_fixture(tmp_path / "warning.pdf", make_pdf_bytes(["text", ""]))
    result = PdfService(Settings(environment="test")).extract_pdf_text(path)

    assert result.status == "success"
    assert result.warnings == ["Page 2 contains no extractable text"]
