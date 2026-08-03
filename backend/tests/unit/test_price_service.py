from datetime import date

import pytest

from app.core.config import Settings
from app.core.exceptions import ProviderUnavailableError
from app.schemas.domain import DailyClose, Exchange
from app.services.price_service import PriceService


class FakeMarketDataProvider:
    def __init__(
        self,
        closes: list[DailyClose] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.closes = closes or []
        self.error = error
        self.calls: list[tuple[str, Exchange, date, date]] = []

    async def get_daily_closes(
        self,
        symbol: str,
        exchange: Exchange,
        start_date: date,
        end_date: date,
    ) -> list[DailyClose]:
        self.calls.append((symbol, exchange, start_date, end_date))
        if self.error:
            raise self.error
        return self.closes


def close(year: int, month: int, day: int, value: float) -> DailyClose:
    return DailyClose(trading_date=date(year, month, day), close=value)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("event_date", "closes", "expected_previous", "expected_next"),
    [
        (
            date(2026, 8, 3),
            [close(2026, 7, 31, 100), close(2026, 8, 4, 110)],
            date(2026, 7, 31),
            date(2026, 8, 4),
        ),
        (
            date(2026, 8, 2),
            [close(2026, 7, 31, 100), close(2026, 8, 3, 110)],
            date(2026, 7, 31),
            date(2026, 8, 3),
        ),
        (
            date(2026, 8, 5),
            [close(2026, 8, 4, 100), close(2026, 8, 6, 110)],
            date(2026, 8, 4),
            date(2026, 8, 6),
        ),
    ],
)
async def test_weekday_weekend_and_holiday_sessions(
    event_date: date,
    closes: list[DailyClose],
    expected_previous: date,
    expected_next: date,
) -> None:
    result = await PriceService(
        Settings(environment="test"),
        FakeMarketDataProvider(closes),
    ).get_price_reaction("INFY", "NSE", event_date)

    assert result.status == "available"
    assert result.previous_trading_date == expected_previous
    assert result.next_trading_date == expected_next
    assert result.percentage_change == 10.0


@pytest.mark.anyio
async def test_correct_percentage_and_rounding() -> None:
    provider = FakeMarketDataProvider([close(2026, 8, 1, 123.45), close(2026, 8, 3, 127.89)])
    result = await PriceService(Settings(environment="test"), provider).get_price_reaction(
        "INFY", "NSE", date(2026, 8, 2)
    )

    assert result.percentage_change == 3.6
    assert "does not establish" in (result.note or "")
    assert (provider.calls[0][3] - provider.calls[0][2]).days == 14


@pytest.mark.anyio
async def test_missing_data_is_unavailable() -> None:
    result = await PriceService(
        Settings(environment="test"),
        FakeMarketDataProvider([close(2026, 8, 1, 100)]),
    ).get_price_reaction("INFY", "NSE", date(2026, 8, 2))

    assert result.status == "unavailable"
    assert result.percentage_change is None


@pytest.mark.anyio
async def test_missing_symbol_does_not_call_provider() -> None:
    provider = FakeMarketDataProvider()
    result = await PriceService(Settings(environment="test"), provider).get_price_reaction(
        None, "NSE", date(2026, 8, 2)
    )

    assert result.status == "unavailable"
    assert provider.calls == []


@pytest.mark.anyio
async def test_provider_failure_is_unavailable() -> None:
    result = await PriceService(
        Settings(environment="test"),
        FakeMarketDataProvider(error=ProviderUnavailableError("failed")),
    ).get_price_reaction("INFY", "NSE", date(2026, 8, 2))

    assert result.status == "unavailable"


@pytest.mark.anyio
async def test_zero_denominator_is_unavailable() -> None:
    result = await PriceService(
        Settings(environment="test"),
        FakeMarketDataProvider([close(2026, 8, 1, 0), close(2026, 8, 3, 10)]),
    ).get_price_reaction("INFY", "NSE", date(2026, 8, 2))

    assert result.status == "unavailable"
    assert "zero" in (result.note or "")
