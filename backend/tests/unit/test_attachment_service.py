from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import (
    AttachmentUnavailableError,
    FileTooLargeError,
    UnsafeDownloadError,
)
from app.services.attachment_service import AttachmentService

PDF_BYTES = b"%PDF-1.4\n% attachment fixture\n%%EOF"


async def public_resolver(_: str, __: int) -> list[str]:
    return ["93.184.216.34"]


def make_service(
    tmp_path: Path,
    handler: httpx.MockTransport,
    **settings_values: object,
) -> tuple[AttachmentService, httpx.AsyncClient]:
    settings = Settings(environment="test", **settings_values)
    client = httpx.AsyncClient(transport=handler)
    return (
        AttachmentService(
            settings,
            client=client,
            resolver=public_resolver,
            temp_directory=tmp_path,
        ),
        client,
    )


@pytest.mark.anyio
async def test_valid_pdf_download_and_cleanup(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200, content=PDF_BYTES, headers={"Content-Type": "application/pdf"}
        )
    )
    service, client = make_service(tmp_path, transport)

    attachment = await service.download_pdf("https://www.bseindia.com/filing.pdf")
    assert attachment.local_path.read_bytes() == PDF_BYTES
    service.cleanup(attachment)
    await client.aclose()

    assert list(tmp_path.iterdir()) == []


@pytest.mark.anyio
async def test_safe_redirect_is_followed(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/final.pdf"})
        return httpx.Response(200, content=PDF_BYTES, headers={"Content-Type": "application/pdf"})

    service, client = make_service(tmp_path, httpx.MockTransport(handler))
    attachment = await service.download_pdf("https://www.bseindia.com/start")
    service.cleanup(attachment)
    await client.aclose()

    assert attachment.source_url.endswith("/final.pdf")


@pytest.mark.anyio
async def test_redirect_limit_is_enforced(tmp_path: Path) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(302, headers={"Location": "/again"}))
    service, client = make_service(tmp_path, transport, max_redirects=1)

    with pytest.raises(UnsafeDownloadError, match="redirect limit"):
        await service.download_pdf("https://www.bseindia.com/start")
    await client.aclose()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("headers", "content", "error_type"),
    [
        ({"Content-Type": "text/html"}, b"<html></html>", UnsafeDownloadError),
        ({"Content-Type": "application/pdf"}, b"<html></html>", UnsafeDownloadError),
        ({"Content-Type": "application/pdf"}, b"", UnsafeDownloadError),
        (
            {"Content-Type": "application/pdf", "Content-Length": "100"},
            PDF_BYTES,
            FileTooLargeError,
        ),
    ],
)
async def test_invalid_responses_are_rejected(
    tmp_path: Path,
    headers: dict[str, str],
    content: bytes,
    error_type: type[Exception],
) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=content, headers=headers))
    service, client = make_service(tmp_path, transport, max_download_bytes=50)

    with pytest.raises(error_type):
        await service.download_pdf("https://www.bseindia.com/filing.pdf")
    await client.aclose()

    assert list(tmp_path.iterdir()) == []


@pytest.mark.anyio
async def test_private_ip_and_localhost_are_rejected(tmp_path: Path) -> None:
    async def private_resolver(_: str, __: int) -> list[str]:
        return ["127.0.0.1"]

    settings = Settings(environment="test")
    service = AttachmentService(settings, resolver=private_resolver, temp_directory=tmp_path)

    with pytest.raises(UnsafeDownloadError):
        await service.validate_remote_url("https://example.com/file.pdf")
    with pytest.raises(UnsafeDownloadError):
        await service.validate_remote_url("https://localhost/file.pdf")


@pytest.mark.anyio
async def test_timeout_is_controlled(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    service, client = make_service(tmp_path, httpx.MockTransport(handler))

    with pytest.raises(AttachmentUnavailableError, match="timed out"):
        await service.download_pdf("https://www.bseindia.com/filing.pdf")
    await client.aclose()
