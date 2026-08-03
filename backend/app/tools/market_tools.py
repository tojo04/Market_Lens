from datetime import date

from app.schemas.domain import Exchange, PriceReaction
from app.services.price_service import PriceService


async def get_price_reaction(
    symbol: str | None,
    exchange: Exchange,
    announcement_date: date,
    price_service: PriceService,
) -> PriceReaction:
    """Calculate nearby session-to-session price reaction using application arithmetic."""
    return await price_service.get_price_reaction(symbol, exchange, announcement_date)
