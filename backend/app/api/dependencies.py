from functools import lru_cache

from openai import AsyncOpenAI

from app.agents.announcement_agent import AnnouncementAgent, OpenAIClient
from app.core.config import get_settings
from app.core.exceptions import AnalysisProviderError
from app.providers.announcements.base import AnnouncementProvider
from app.providers.announcements.bse import BSEAnnouncementProvider
from app.providers.market_data.base import MarketDataProvider
from app.providers.market_data.yfinance import YFinanceMarketDataProvider
from app.repositories.company_repository import CompanyRepository
from app.services.analysis_service import AnalysisService
from app.services.announcement_service import AnnouncementService
from app.services.attachment_service import AttachmentService
from app.services.company_service import CompanyService
from app.services.document_service import DocumentService
from app.services.pdf_service import PdfService
from app.services.price_service import PriceService


@lru_cache
def get_company_service() -> CompanyService:
    return CompanyService(CompanyRepository.from_json())


@lru_cache
def get_announcement_provider() -> AnnouncementProvider:
    return BSEAnnouncementProvider(get_settings(), get_company_service())


@lru_cache
def get_announcement_service() -> AnnouncementService:
    return AnnouncementService(get_announcement_provider(), get_company_service())


@lru_cache
def get_document_service() -> DocumentService:
    settings = get_settings()
    return DocumentService(
        settings,
        AttachmentService(settings),
        PdfService(settings),
    )


@lru_cache
def get_market_data_provider() -> MarketDataProvider:
    return YFinanceMarketDataProvider(get_settings())


@lru_cache
def get_price_service() -> PriceService:
    return PriceService(get_settings(), get_market_data_provider())


@lru_cache
def get_openai_client() -> OpenAIClient:
    settings = get_settings()
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value().strip():
        raise AnalysisProviderError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.analysis_timeout_seconds,
        max_retries=1,
    )


@lru_cache
def get_announcement_agent() -> AnnouncementAgent:
    return AnnouncementAgent(get_settings(), get_openai_client(), get_price_service())


@lru_cache
def get_analysis_service() -> AnalysisService:
    return AnalysisService(
        get_company_service(),
        get_announcement_service(),
        get_document_service(),
        get_announcement_agent(),
    )
