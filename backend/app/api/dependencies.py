from functools import lru_cache

from app.core.config import get_settings
from app.providers.announcements.base import AnnouncementProvider
from app.providers.announcements.bse import BSEAnnouncementProvider
from app.providers.market_data.base import MarketDataProvider
from app.providers.market_data.yfinance import YFinanceMarketDataProvider
from app.repositories.company_repository import CompanyRepository
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
