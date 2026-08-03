import asyncio
import ipaddress
import socket
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from app.core.config import Settings
from app.core.exceptions import (
    AttachmentUnavailableError,
    FileTooLargeError,
    ProviderRateLimitError,
    UnsafeDownloadError,
)
from app.schemas.domain import DownloadedAttachment

HostResolver = Callable[[str, int], Awaitable[list[str]]]
ALLOWED_PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream"}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


async def resolve_host(hostname: str, port: int) -> list[str]:
    def lookup() -> list[str]:
        answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        return sorted({answer[4][0] for answer in answers})

    try:
        return await asyncio.to_thread(lookup)
    except socket.gaierror as error:
        raise UnsafeDownloadError("Attachment host could not be resolved") from error


class AttachmentService:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        resolver: HostResolver = resolve_host,
        temp_directory: Path | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._resolver = resolver
        self._temp_directory = temp_directory

    async def download_pdf(self, source_url: str) -> DownloadedAttachment:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=self._timeout(),
            follow_redirects=False,
        )
        try:
            for attempt in range(2):
                try:
                    return await self._download_once(client, source_url)
                except (httpx.TimeoutException, httpx.NetworkError) as error:
                    if attempt == 0:
                        await asyncio.sleep(0.2)
                        continue
                    raise AttachmentUnavailableError("Attachment download timed out") from error
            raise AttachmentUnavailableError("Attachment download failed")
        finally:
            if owns_client:
                await client.aclose()

    async def validate_remote_url(self, value: str) -> httpx.URL:
        try:
            url = httpx.URL(value)
        except httpx.InvalidURL as error:
            raise UnsafeDownloadError("Attachment URL is invalid") from error
        if url.scheme != "https":
            raise UnsafeDownloadError("Attachment URL must use HTTPS")
        if not url.host or url.userinfo:
            raise UnsafeDownloadError("Attachment URL contains unsafe authority information")
        hostname = url.host.casefold().rstrip(".")
        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise UnsafeDownloadError("Local attachment hosts are not allowed")
        addresses = await self._resolver(hostname, url.port or 443)
        if not addresses:
            raise UnsafeDownloadError("Attachment host did not resolve")
        for address in addresses:
            try:
                parsed_address = ipaddress.ip_address(address)
            except ValueError as error:
                raise UnsafeDownloadError("Attachment host resolved unexpectedly") from error
            if not parsed_address.is_global:
                raise UnsafeDownloadError(
                    "Private or non-routable attachment hosts are not allowed"
                )
        return url

    async def _download_once(
        self,
        client: httpx.AsyncClient,
        source_url: str,
    ) -> DownloadedAttachment:
        current_url = await self.validate_remote_url(source_url)
        for redirect_count in range(self._settings.max_redirects + 1):
            request = client.build_request(
                "GET",
                current_url,
                headers={
                    "User-Agent": self._settings.user_agent,
                    "Accept": "application/pdf",
                    "Referer": str(self._settings.bse_site_base_url),
                },
            )
            response = await client.send(request, stream=True)
            if response.status_code in REDIRECT_STATUSES:
                try:
                    location = response.headers.get("Location")
                    if not location or redirect_count >= self._settings.max_redirects:
                        raise UnsafeDownloadError("Attachment redirect limit exceeded")
                    current_url = await self.validate_remote_url(str(response.url.join(location)))
                finally:
                    await response.aclose()
                continue
            try:
                return await self._save_response(response, str(current_url))
            finally:
                await response.aclose()
        raise UnsafeDownloadError("Attachment redirect limit exceeded")

    async def _save_response(
        self,
        response: httpx.Response,
        source_url: str,
    ) -> DownloadedAttachment:
        if response.status_code == 429:
            raise ProviderRateLimitError("Attachment source rate limit reached")
        if response.status_code != 200:
            raise AttachmentUnavailableError(
                f"Attachment source returned HTTP {response.status_code}"
            )
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].casefold()
        if content_type not in ALLOWED_PDF_CONTENT_TYPES:
            raise UnsafeDownloadError("Attachment response is not a supported PDF content type")
        content_length = _parse_content_length(response.headers.get("Content-Length"))
        if content_length is not None and content_length > self._settings.max_download_bytes:
            raise FileTooLargeError("Attachment exceeds the maximum allowed size")

        path: Path | None = None
        size = 0
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".pdf",
                prefix="marketlens-",
                dir=self._temp_directory,
                delete=False,
            ) as temporary:
                path = Path(temporary.name)
                async for chunk in response.aiter_bytes(64 * 1024):
                    size += len(chunk)
                    if size > self._settings.max_download_bytes:
                        raise FileTooLargeError("Attachment exceeds the maximum allowed size")
                    temporary.write(chunk)
            if size == 0:
                raise UnsafeDownloadError("Attachment response was empty")
            assert path is not None
            with path.open("rb") as pdf_file:
                if pdf_file.read(5) != b"%PDF-":
                    raise UnsafeDownloadError("Attachment content is not a valid PDF")
            return DownloadedAttachment(
                source_url=source_url,
                local_path=path,
                content_type=content_type,
                size_bytes=size,
            )
        except BaseException:
            if path is not None:
                path.unlink(missing_ok=True)
            raise

    @staticmethod
    def cleanup(attachment: DownloadedAttachment) -> None:
        attachment.local_path.unlink(missing_ok=True)

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self._settings.http_connect_timeout_seconds,
            read=self._settings.http_read_timeout_seconds,
            write=self._settings.http_write_timeout_seconds,
            pool=self._settings.http_pool_timeout_seconds,
        )


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return max(int(value), 0)
    except ValueError:
        return None
