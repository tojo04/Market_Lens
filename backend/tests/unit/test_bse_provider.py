from collections.abc import Callable
from datetime import date

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import ProviderRateLimitError, ProviderUnavailableError
from app.providers.announcements.bse import BSEAnnouncementProvider
from app.repositories.company_repository import CompanyRepository
from app.services.company_service import CompanyService

PayloadFactory = Callable[[list[dict[str, object]]], dict[str, object]]


@pytest.fixture
def settings() -> Settings:
    return Settings(environment="test", provider_max_results=20)


@pytest.fixture
def company_service() -> CompanyService:
    return CompanyService(CompanyRepository.from_json())


@pytest.fixture
def payload() -> PayloadFactory:
    return lambda rows: {"Table": rows, "Table1": [{"ROWCNT": len(rows)}]}


@pytest.fixture
def valid_row() -> dict[str, object]:
    return {
        "NEWSID": "news-1",
        "SCRIP_CD": 500209,
        "NEWSSUB": "Board meeting outcome",
        "NEWS_DT": "2026-08-02T10:30:00",
        "ATTACHMENTNAME": "filing-one.pdf",
        "CATEGORYNAME": "Company Update",
        "SUBCATNAME": "Board Meeting",
    }


def make_provider(
    settings: Settings,
    company_service: CompanyService,
    handler: httpx.MockTransport,
) -> BSEAnnouncementProvider:
    client = httpx.AsyncClient(
        base_url=str(settings.bse_api_base_url).rstrip("/"),
        transport=handler,
    )

    async def no_sleep(_: float) -> None:
        return None

    return BSEAnnouncementProvider(settings, company_service, client=client, sleep=no_sleep)


def parser_provider(settings: Settings, company_service: CompanyService) -> BSEAnnouncementProvider:
    return BSEAnnouncementProvider(settings, company_service)


@pytest.mark.anyio
async def test_valid_response_is_normalized(
    settings: Settings,
    company_service: CompanyService,
    payload: PayloadFactory,
    valid_row: dict[str, object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["strScrip"] == "500209"
        assert request.headers["User-Agent"] == settings.user_agent
        return httpx.Response(200, json=payload([valid_row]))

    provider = make_provider(settings, company_service, httpx.MockTransport(handler))
    announcements = await provider.get_recent_announcements(
        "500209", date(2026, 8, 1), date(2026, 8, 3)
    )
    await provider._client.aclose()  # type: ignore[union-attr]

    assert announcements[0].title == "Board meeting outcome"
    assert announcements[0].published_at.utcoffset() is not None
    assert announcements[0].attachment_url == (
        "https://www.bseindia.com/xml-data/corpfiling/AttachLive/filing-one.pdf"
    )


@pytest.mark.parametrize(
    ("mutation", "expected_count"),
    [
        (lambda row: {**row, "SCRIP_CD": 500325}, 0),
        (lambda row: {**row, "NEWS_DT": "2026-07-01T10:30:00"}, 0),
        (lambda row: {**row, "NEWSSUB": ""}, 0),
        (lambda row: {**row, "ATTACHMENTNAME": ""}, 1),
    ],
)
def test_row_filtering_and_missing_fields(
    settings: Settings,
    company_service: CompanyService,
    payload: PayloadFactory,
    valid_row: dict[str, object],
    mutation: Callable[[dict[str, object]], dict[str, object]],
    expected_count: int,
) -> None:
    provider = parser_provider(settings, company_service)
    company = company_service.get_by_id("500209")
    announcements = provider.parse_response(
        payload([mutation(valid_row)]),
        company,
        date(2026, 8, 1),
        date(2026, 8, 3),
        20,
    )

    assert len(announcements) == expected_count
    if expected_count and not mutation(valid_row).get("ATTACHMENTNAME"):
        assert announcements[0].attachment_url is None


def test_empty_duplicates_and_limit(
    settings: Settings,
    company_service: CompanyService,
    payload: PayloadFactory,
    valid_row: dict[str, object],
) -> None:
    provider = parser_provider(settings, company_service)
    company = company_service.get_by_id("500209")
    empty = provider.parse_response(payload([]), company, date(2026, 8, 1), date(2026, 8, 3), 20)
    duplicate_rows = [
        valid_row,
        valid_row,
        {**valid_row, "NEWSID": "news-2", "NEWS_DT": "2026-08-03T10:30:00"},
    ]
    limited = provider.parse_response(
        payload(duplicate_rows), company, date(2026, 8, 1), date(2026, 8, 3), 1
    )

    assert empty == []
    assert len(limited) == 1
    assert limited[0].announcement_id == "news-2"


def test_unexpected_schema_is_controlled(
    settings: Settings,
    company_service: CompanyService,
) -> None:
    provider = parser_provider(settings, company_service)

    with pytest.raises(ProviderUnavailableError, match="schema changed"):
        provider.parse_response(
            {"Table": {}},
            company_service.get_by_id("500209"),
            date(2026, 8, 1),
            date(2026, 8, 3),
            20,
        )


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["timeout", "malformed"])
async def test_network_and_malformed_failures_are_controlled(
    settings: Settings,
    company_service: CompanyService,
    failure: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, content=b"not-json")

    provider = make_provider(settings, company_service, httpx.MockTransport(handler))
    with pytest.raises(ProviderUnavailableError):
        await provider.get_recent_announcements("500209", date(2026, 8, 1), date(2026, 8, 3))
    await provider._client.aclose()  # type: ignore[union-attr]


@pytest.mark.anyio
async def test_rate_limit_is_typed(
    settings: Settings,
    company_service: CompanyService,
) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(429, headers={"Retry-After": "30"}))
    provider = make_provider(settings, company_service, transport)

    with pytest.raises(ProviderRateLimitError) as caught:
        await provider.get_recent_announcements("500209", date(2026, 8, 1), date(2026, 8, 3))
    await provider._client.aclose()  # type: ignore[union-attr]

    assert caught.value.retry_after_seconds == 30
