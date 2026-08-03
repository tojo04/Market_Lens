from datetime import date

import pandas as pd
import pytest

from app.core.config import Settings
from app.core.exceptions import MarketDataUnavailableError, ProviderUnavailableError
from app.providers.market_data.yfinance import YFinanceMarketDataProvider


@pytest.mark.anyio
async def test_valid_nse_symbol_is_mapped_and_normalized() -> None:
    calls: list[str] = []

    def downloader(ticker: str, **_: object) -> pd.DataFrame:
        calls.append(ticker)
        return pd.DataFrame(
            {"Close": [1500.25, 1510.5]},
            index=pd.to_datetime(["2026-08-03", "2026-08-04"]),
        )

    provider = YFinanceMarketDataProvider(Settings(environment="test"), downloader=downloader)
    closes = await provider.get_daily_closes("infy", "NSE", date(2026, 8, 3), date(2026, 8, 4))

    assert calls == ["INFY.NS"]
    assert closes[0].close == 1500.25
    assert closes[1].trading_date == date(2026, 8, 4)


@pytest.mark.parametrize(
    ("symbol", "exchange", "ticker"),
    [("SBIN", "NSE", "SBIN.NS"), ("500112", "BSE", "500112.BO")],
)
def test_deterministic_ticker_mapping(symbol: str, exchange: str, ticker: str) -> None:
    assert YFinanceMarketDataProvider.resolve_ticker(symbol, exchange) == ticker  # type: ignore[arg-type]


def test_bse_symbol_without_security_code_is_unavailable() -> None:
    with pytest.raises(MarketDataUnavailableError):
        YFinanceMarketDataProvider.resolve_ticker("INFY", "BSE")


@pytest.mark.anyio
async def test_provider_exception_is_typed() -> None:
    def downloader(_: str, **__: object) -> pd.DataFrame:
        raise RuntimeError("provider failed")

    provider = YFinanceMarketDataProvider(Settings(environment="test"), downloader=downloader)

    with pytest.raises(ProviderUnavailableError):
        await provider.get_daily_closes("INFY", "NSE", date(2026, 8, 3), date(2026, 8, 4))


@pytest.mark.anyio
async def test_missing_close_column_is_typed() -> None:
    provider = YFinanceMarketDataProvider(
        Settings(environment="test"),
        downloader=lambda *_args, **_kwargs: pd.DataFrame(
            {"Open": [1500]}, index=pd.to_datetime(["2026-08-03"])
        ),
    )

    with pytest.raises(ProviderUnavailableError, match="close column"):
        await provider.get_daily_closes("INFY", "NSE", date(2026, 8, 3), date(2026, 8, 4))
