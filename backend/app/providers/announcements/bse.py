import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.core.exceptions import (
    AttachmentUnavailableError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.schemas.domain import AnnouncementSummary, CompanyMatch, DownloadedAttachment
from app.services.company_service import CompanyService

logger = logging.getLogger(__name__)
INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")
SleepCallable = Callable[[float], Awaitable[None]]


class BSEAnnouncementProvider:
    """Adapter for BSE's official corporate-announcement JSON surface.

    BSE terms, allowed usage, and endpoint stability must be reviewed before public deployment.
    The adapter deliberately performs no browser automation or anti-bot bypass.
    """

    endpoint_path = "/AnnSubCategoryGetData/w"

    def __init__(
        self,
        settings: Settings,
        company_service: CompanyService,
        client: httpx.AsyncClient | None = None,
        sleep: SleepCallable = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._company_service = company_service
        self._client = client
        self._sleep = sleep

    async def search_companies(self, query: str, limit: int = 10) -> list[CompanyMatch]:
        return self._company_service.search(query, limit)

    async def get_recent_announcements(
        self,
        company_id: str,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 20,
    ) -> list[AnnouncementSummary]:
        company = self._company_service.get_by_id(company_id)
        end_date = to_date or date.today()
        start_date = from_date or end_date - timedelta(days=30)
        if start_date > end_date:
            raise ValueError("from_date cannot be after to_date")
        bounded_limit = min(max(limit, 1), self._settings.provider_max_results)
        payload = await self._request_announcements(company, start_date, end_date)
        return self.parse_response(payload, company, start_date, end_date, bounded_limit)

    async def download_attachment(self, announcement_id: str) -> DownloadedAttachment:
        raise AttachmentUnavailableError(
            "Attachment download requires a server-resolved announcement summary"
        )

    async def _request_announcements(
        self,
        company: CompanyMatch,
        from_date: date,
        to_date: date,
    ) -> Mapping[str, Any]:
        params = {
            "pageno": "1",
            "strCat": "-1",
            "strPrevDate": from_date.strftime("%Y%m%d"),
            "strScrip": company.security_code or company.company_id,
            "strSearch": "P",
            "strToDate": to_date.strftime("%Y%m%d"),
            "strType": "C",
            "subcategory": "-1",
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            base_url=str(self._settings.bse_api_base_url).rstrip("/"),
            timeout=self._timeout(),
            follow_redirects=False,
        )
        try:
            for attempt in range(2):
                try:
                    response = await client.get(
                        self.endpoint_path,
                        params=params,
                        headers={
                            "User-Agent": self._settings.user_agent,
                            "Accept": "application/json",
                            "Referer": str(self._settings.bse_site_base_url),
                        },
                    )
                except (httpx.ConnectError, httpx.ReadTimeout) as error:
                    if attempt == 0:
                        await self._sleep(0.2)
                        continue
                    raise ProviderUnavailableError("BSE announcement service timed out") from error
                if response.status_code == 429:
                    retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                    raise ProviderRateLimitError(
                        "BSE announcement service rate limit reached",
                        retry_after_seconds=retry_after,
                    )
                if response.status_code in {500, 502, 503, 504} and attempt == 0:
                    await self._sleep(0.2)
                    continue
                if response.status_code != 200:
                    raise ProviderUnavailableError(
                        f"BSE announcement service returned HTTP {response.status_code}"
                    )
                try:
                    payload = response.json()
                except ValueError as error:
                    raise ProviderUnavailableError("BSE returned malformed JSON") from error
                if not isinstance(payload, Mapping):
                    raise ProviderUnavailableError("BSE returned an unexpected response schema")
                return payload
            raise ProviderUnavailableError("BSE announcement service is unavailable")
        finally:
            if owns_client:
                await client.aclose()

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self._settings.http_connect_timeout_seconds,
            read=self._settings.http_read_timeout_seconds,
            write=self._settings.http_write_timeout_seconds,
            pool=self._settings.http_pool_timeout_seconds,
        )

    def parse_response(
        self,
        payload: Mapping[str, Any],
        company: CompanyMatch,
        from_date: date,
        to_date: date,
        limit: int,
    ) -> list[AnnouncementSummary]:
        rows = payload.get("Table")
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise ProviderUnavailableError("BSE announcement response schema changed")
        announcements: list[AnnouncementSummary] = []
        seen_ids: set[str] = set()
        for raw_row in rows:
            if not isinstance(raw_row, Mapping):
                continue
            parsed = self._parse_row(raw_row, company)
            if parsed is None:
                continue
            if parsed.announcement_id in seen_ids:
                continue
            if not from_date <= parsed.published_at.date() <= to_date:
                continue
            seen_ids.add(parsed.announcement_id)
            announcements.append(parsed)
        announcements.sort(key=lambda item: item.published_at, reverse=True)
        return announcements[:limit]

    def _parse_row(
        self,
        row: Mapping[str, Any],
        company: CompanyMatch,
    ) -> AnnouncementSummary | None:
        news_id = str(row.get("NEWSID") or "").strip()
        title = str(row.get("NEWSSUB") or "").strip()
        row_security_code = str(row.get("SCRIP_CD") or "").strip()
        if not news_id or not title or row_security_code != company.security_code:
            return None
        published_at = _parse_bse_datetime(row.get("NEWS_DT") or row.get("DT_TM"))
        if published_at is None:
            return None
        attachment_name = str(row.get("ATTACHMENTNAME") or "").strip()
        attachment_url = None
        if attachment_name.lower().endswith(".pdf") and "/" not in attachment_name:
            attachment_url = (
                f"{str(self._settings.bse_attachment_base_url).rstrip('/')}/"
                f"{quote(attachment_name)}"
            )
        detail_url = (
            f"{str(self._settings.bse_site_base_url).rstrip('/')}/corporates/anndet_new.aspx"
            f"?newsid={quote(news_id)}&scripcode={quote(row_security_code)}"
        )
        category = str(row.get("SUBCATNAME") or row.get("CATEGORYNAME") or "").strip() or None
        return AnnouncementSummary(
            provider="bse",
            announcement_id=news_id,
            company_id=company.company_id,
            security_code=company.security_code,
            symbol=company.symbol,
            company_name=company.company_name,
            exchange="BSE",
            title=title,
            category=category,
            published_at=published_at,
            detail_url=detail_url,
            attachment_url=attachment_url,
            attachment_type="application/pdf" if attachment_url else None,
        )


def _parse_bse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    return parsed.replace(tzinfo=INDIA_TIMEZONE) if parsed.tzinfo is None else parsed


def _parse_retry_after(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return max(int(value), 0)
    except ValueError:
        return None
