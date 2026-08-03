from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app.api.dependencies import get_announcement_service
from app.core.exceptions import ProviderUnavailableError
from app.main import app
from app.schemas.domain import AnnouncementSummary

client = TestClient(app)


class StubAnnouncementService:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def list_recent(
        self,
        company_id: str,
        from_date: date | None,
        to_date: date | None,
        limit: int,
    ) -> list[AnnouncementSummary]:
        if self.fail:
            raise ProviderUnavailableError("BSE is temporarily unavailable")
        return [
            AnnouncementSummary(
                provider="bse",
                announcement_id="news-1",
                company_id=company_id,
                security_code=company_id,
                symbol="INFY",
                company_name="Infosys Limited",
                exchange="BSE",
                title="Board meeting outcome",
                published_at=datetime(2026, 8, 2, 10, 30, tzinfo=UTC),
            )
        ]


def test_announcement_list_endpoint() -> None:
    app.dependency_overrides[get_announcement_service] = lambda: StubAnnouncementService()
    try:
        response = client.get("/api/companies/500209/announcements")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["announcement_id"] == "news-1"


def test_provider_failure_offers_fallback() -> None:
    app.dependency_overrides[get_announcement_service] = lambda: StubAnnouncementService(fail=True)
    try:
        response = client.get("/api/companies/500209/announcements")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_unavailable"
    assert response.json()["error"]["fallback_available"] is True
