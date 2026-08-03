from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_service
from app.core.config import Settings
from app.core.exceptions import (
    AnalysisProviderError,
    AnalysisValidationError,
    AnnouncementNotFoundError,
    ProviderUnavailableError,
    UnsafeDownloadError,
)
from app.main import app
from app.schemas.analysis import (
    REQUIRED_DISCLAIMER,
    AnalysisInput,
    AnalyzeAnnouncementRequest,
    AnnouncementAnalysis,
)
from app.schemas.domain import AnnouncementSummary, ExtractionResult, PageText, PriceReaction
from app.services.analysis_service import AnalysisService
from app.services.attachment_service import AttachmentService
from app.services.document_service import DocumentService
from app.services.pdf_service import PdfService
from tests.helpers import make_pdf_bytes

client = TestClient(app)


def announcement(
    attachment_url: str | None = "https://www.bseindia.com/filing.pdf",
) -> AnnouncementSummary:
    return AnnouncementSummary(
        provider="bse",
        announcement_id="news-1",
        company_id="500209",
        security_code="500209",
        symbol="INFY",
        company_name="Infosys Limited",
        exchange="BSE",
        title="Quarterly results",
        category="Financial Results",
        published_at=datetime(2026, 8, 3, 10, 30, tzinfo=UTC),
        detail_url="https://www.bseindia.com/announcement/news-1",
        attachment_url=attachment_url,
        attachment_type="application/pdf" if attachment_url else None,
    )


def analysis_for(
    analysis_input: AnalysisInput,
    price_reaction: PriceReaction | None = None,
) -> AnnouncementAnalysis:
    return AnnouncementAnalysis(
        announcement_category="financial_results",
        title="Quarterly results",
        summary="The company published quarterly results.",
        important_facts=[
            {
                "label": "Revenue",
                "value": "₹1,250 crore",
                "source_excerpt": "Revenue was ₹1,250 crore",
                "page_number": 1,
            }
        ],
        why_it_matters=["The filing updates reported performance."],
        positive_signals=["Reported revenue was positive."],
        risks=["The supplied filing is a point-in-time disclosure."],
        price_reaction=price_reaction
        or PriceReaction(status="unavailable", note="Market data unavailable"),
        confidence="high",
        limitations=["Only the supplied filing was analyzed."],
        source=analysis_input.source,
        disclaimer=REQUIRED_DISCLAIMER,
    )


class StubCompanyService:
    def get_by_id(self, company_id: str) -> object:
        if company_id != "500209":
            raise AssertionError("unexpected company")
        return object()


class StubAnnouncementService:
    def __init__(
        self,
        result: AnnouncementSummary | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or announcement()
        self.error = error

    async def resolve_announcement(
        self,
        company_id: str,
        announcement_id: str,
    ) -> AnnouncementSummary:
        if self.error:
            raise self.error
        assert company_id == "500209"
        assert announcement_id == "news-1"
        return self.result


class StubDocumentService:
    def __init__(
        self,
        result: ExtractionResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or ExtractionResult(
            status="success",
            page_count=1,
            pages=[PageText(page_number=1, text="Revenue was ₹1,250 crore")],
        )
        self.error = error
        self.remote_urls: list[str] = []
        self.upload_names: list[str | None] = []

    async def extract_remote(self, source_url: str) -> ExtractionResult:
        self.remote_urls.append(source_url)
        if self.error:
            raise self.error
        return self.result

    async def extract_upload(self, upload: Any) -> ExtractionResult:
        self.upload_names.append(upload.filename)
        if self.error:
            raise self.error
        return self.result


class StubAgent:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.inputs: list[AnalysisInput] = []

    async def analyze(self, analysis_input: AnalysisInput) -> AnnouncementAnalysis:
        self.inputs.append(analysis_input)
        if self.error:
            raise self.error
        return analysis_for(analysis_input)


class StubAnalysisRepository:
    def __init__(self) -> None:
        self.saved: list[AnnouncementAnalysis] = []

    def save(self, analysis: AnnouncementAnalysis) -> None:
        self.saved.append(analysis)


def make_service(
    *,
    announcement_service: Any | None = None,
    document_service: Any | None = None,
    agent: Any | None = None,
    analysis_repository: Any | None = None,
) -> AnalysisService:
    return AnalysisService(
        StubCompanyService(),  # type: ignore[arg-type]
        announcement_service or StubAnnouncementService(),  # type: ignore[arg-type]
        document_service or StubDocumentService(),  # type: ignore[arg-type]
        agent or StubAgent(),  # type: ignore[arg-type]
        analysis_repository or StubAnalysisRepository(),  # type: ignore[arg-type]
    )


def request_with_service(
    service: AnalysisService,
    path: str,
    **request_kwargs: Any,
) -> Any:
    app.dependency_overrides[get_analysis_service] = lambda: service
    try:
        return client.post(path, **request_kwargs)
    finally:
        app.dependency_overrides.clear()


def test_full_automatic_analysis_success() -> None:
    documents = StubDocumentService()
    agent = StubAgent()
    repository = StubAnalysisRepository()
    response = request_with_service(
        make_service(
            document_service=documents,
            agent=agent,
            analysis_repository=repository,
        ),
        "/api/analyses/from-announcement",
        json={"provider": "bse", "company_id": "500209", "announcement_id": "news-1"},
    )

    assert response.status_code == 200
    assert response.json()["source"]["announcement_id"] == "news-1"
    assert response.json()["important_facts"][0]["value"] == "₹1,250 crore"
    assert documents.remote_urls == ["https://www.bseindia.com/filing.pdf"]
    assert agent.inputs[0].pages[0].page_number == 1
    assert len(repository.saved) == 1


def test_manual_upload_analysis_success() -> None:
    documents = StubDocumentService()
    repository = StubAnalysisRepository()
    response = request_with_service(
        make_service(document_service=documents, analysis_repository=repository),
        "/api/analyses/from-upload",
        files={"file": ("filing.pdf", b"%PDF-fixture", "application/pdf")},
        data={
            "symbol": "INFY",
            "exchange": "BSE",
            "announcement_date": "2026-08-03",
            "company_name": "Infosys Limited",
            "security_code": "500209",
        },
    )

    assert response.status_code == 200
    assert response.json()["source"]["provider"] == "manual_upload"
    assert response.json()["source"]["company_name"] == "Infosys Limited"
    assert documents.upload_names == ["filing.pdf"]
    assert len(repository.saved) == 1


@pytest.mark.parametrize(
    ("service", "expected_status", "expected_code"),
    [
        (
            make_service(announcement_service=StubAnnouncementService(result=announcement(None))),
            404,
            "attachment_unavailable",
        ),
        (
            make_service(
                announcement_service=StubAnnouncementService(
                    error=ProviderUnavailableError("provider timeout")
                )
            ),
            503,
            "provider_unavailable",
        ),
        (
            make_service(
                announcement_service=StubAnnouncementService(
                    error=ProviderUnavailableError("provider failed")
                )
            ),
            503,
            "provider_unavailable",
        ),
        (
            make_service(
                announcement_service=StubAnnouncementService(
                    error=AnnouncementNotFoundError("announcement not found")
                )
            ),
            404,
            "announcement_not_found",
        ),
        (
            make_service(
                document_service=StubDocumentService(error=UnsafeDownloadError("unsafe redirect"))
            ),
            400,
            "unsafe_attachment_url",
        ),
        (
            make_service(
                document_service=StubDocumentService(
                    result=ExtractionResult(
                        status="scanned_pdf_unsupported",
                        page_count=1,
                        pages=[],
                    )
                )
            ),
            422,
            "scanned_pdf_unsupported",
        ),
        (
            make_service(agent=StubAgent(error=AnalysisProviderError("OpenAI failed"))),
            502,
            "analysis_provider_error",
        ),
        (
            make_service(agent=StubAgent(error=AnalysisValidationError("invalid output"))),
            502,
            "analysis_validation_error",
        ),
    ],
)
def test_typed_automatic_analysis_failures(
    service: AnalysisService,
    expected_status: int,
    expected_code: str,
) -> None:
    response = request_with_service(
        service,
        "/api/analyses/from-announcement",
        json={"provider": "bse", "company_id": "500209", "announcement_id": "news-1"},
    )

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["error"]["request_id"]


def test_market_data_unavailable_is_successful_analysis() -> None:
    response = request_with_service(
        make_service(),
        "/api/analyses/from-announcement",
        json={"provider": "bse", "company_id": "500209", "announcement_id": "news-1"},
    )

    assert response.status_code == 200
    assert response.json()["price_reaction"]["status"] == "unavailable"


def test_client_supplied_attachment_url_is_rejected() -> None:
    response = request_with_service(
        make_service(),
        "/api/analyses/from-announcement",
        json={
            "provider": "bse",
            "company_id": "500209",
            "announcement_id": "news-1",
            "attachment_url": "http://127.0.0.1/private.pdf",
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_full_automatic_workflow_cleans_downloaded_pdf(tmp_path: Path) -> None:
    settings = Settings(environment="test")
    pdf_bytes = make_pdf_bytes(["Revenue was ₹1,250 crore"])
    client_http = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                content=pdf_bytes,
                headers={"Content-Type": "application/pdf"},
            )
        )
    )

    async def public_resolver(_: str, __: int) -> list[str]:
        return ["93.184.216.34"]

    attachment_service = AttachmentService(
        settings,
        client=client_http,
        resolver=public_resolver,
        temp_directory=tmp_path,
    )
    document_service = DocumentService(
        settings,
        attachment_service,
        PdfService(settings),
        temp_directory=tmp_path,
    )
    service = make_service(document_service=document_service)

    result = await service.analyze_announcement(
        AnalyzeAnnouncementRequest(
            provider="bse",
            company_id="500209",
            announcement_id="news-1",
        )
    )
    await client_http.aclose()

    assert result.source.announcement_id == "news-1"
    assert list(tmp_path.iterdir()) == []
