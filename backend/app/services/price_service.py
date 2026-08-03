from datetime import date, timedelta

from app.core.config import Settings
from app.core.exceptions import MarketDataUnavailableError, ProviderUnavailableError
from app.providers.market_data.base import MarketDataProvider
from app.schemas.domain import DailyClose, Exchange, PriceReaction


class PriceService:
    def __init__(self, settings: Settings, provider: MarketDataProvider) -> None:
        self._settings = settings
        self._provider = provider

    async def get_price_reaction(
        self,
        symbol: str | None,
        exchange: Exchange,
        announcement_date: date,
    ) -> PriceReaction:
        if not symbol or not symbol.strip():
            return _unavailable("A verified market symbol was not supplied")
        window = self._settings.market_event_window_days
        try:
            closes = await self._provider.get_daily_closes(
                symbol=symbol,
                exchange=exchange,
                start_date=announcement_date - timedelta(days=window),
                end_date=announcement_date + timedelta(days=window),
            )
        except (MarketDataUnavailableError, ProviderUnavailableError):
            return _unavailable("Nearby market data is unavailable; no ticker was substituted")
        previous = _latest_before(closes, announcement_date)
        following = _earliest_after(closes, announcement_date)
        if previous is None or following is None:
            return PriceReaction(
                previous_trading_date=previous.trading_date if previous else None,
                previous_close=previous.close if previous else None,
                next_trading_date=following.trading_date if following else None,
                next_close=following.close if following else None,
                status="unavailable",
                note="Insufficient sessions in the bounded event window",
            )
        if previous.close == 0:
            return PriceReaction(
                previous_trading_date=previous.trading_date,
                previous_close=previous.close,
                next_trading_date=following.trading_date,
                next_close=following.close,
                status="unavailable",
                note="Price reaction cannot be calculated from a zero previous close",
            )
        percentage_change = round(
            ((following.close - previous.close) / previous.close) * 100,
            2,
        )
        return PriceReaction(
            previous_trading_date=previous.trading_date,
            previous_close=previous.close,
            next_trading_date=following.trading_date,
            next_close=following.close,
            percentage_change=percentage_change,
            status="available",
            note=(
                "Nearby price reaction only; this does not establish that the announcement "
                "caused the move"
            ),
        )


def _latest_before(closes: list[DailyClose], event_date: date) -> DailyClose | None:
    eligible = (close for close in closes if close.trading_date < event_date)
    return max(eligible, key=lambda close: close.trading_date, default=None)


def _earliest_after(closes: list[DailyClose], event_date: date) -> DailyClose | None:
    eligible = (close for close in closes if close.trading_date > event_date)
    return min(eligible, key=lambda close: close.trading_date, default=None)


def _unavailable(note: str) -> PriceReaction:
    return PriceReaction(status="unavailable", note=note)
