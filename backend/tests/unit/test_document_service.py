from io import BytesIO
from pathlib import Path

import httpx
import pytest
from starlette.datastructures import Headers, UploadFile

from app.core.config import Settings
from app.services.attachment_service import AttachmentService
from app.services.document_service import DocumentService
from app.services.pdf_service import PdfService
from tests.helpers import make_pdf_bytes


async def public_resolver(_: str, __: int) -> list[str]:
    return ["93.184.216.34"]


@pytest.mark.anyio
async def test_remote_and_upload_share_extractor_and_cleanup(tmp_path: Path) -> None:
    pdf_bytes = make_pdf_bytes(["Official announcement"])
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                content=pdf_bytes,
                headers={"Content-Type": "application/pdf"},
            )
        )
    )
    settings = Settings(environment="test")
    attachment_service = AttachmentService(
        settings,
        client=client,
        resolver=public_resolver,
        temp_directory=tmp_path,
    )
    service = DocumentService(
        settings,
        attachment_service,
        PdfService(settings),
        temp_directory=tmp_path,
    )

    remote_result = await service.extract_remote("https://www.bseindia.com/filing.pdf")
    upload = UploadFile(
        BytesIO(pdf_bytes),
        filename="announcement.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    upload_result = await service.extract_upload(upload)
    await client.aclose()

    assert remote_result.pages[0].text == upload_result.pages[0].text
    assert list(tmp_path.iterdir()) == []
