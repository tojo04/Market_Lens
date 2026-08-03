import asyncio
import re
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from app.core.config import Settings
from app.core.exceptions import MarketDataUnavailableError, ProviderUnavailableError
from app.schemas.domain import DailyClose, Exchange

NSE_SYMBOL = re.compile(r"^[A-Z0-9&-]{1,20}$")
BSE_SECURITY_CODE = re.compile(r"^\d{6}$")
Downloader = Callable[..., Any]


class YFinanceMarketDataProvider:
    """Replaceable prototype adapter; it is never called by the automated test suite."""

    def __init__(
        self,
        settings: Settings,
        downloader: Downloader = yf.download,
    ) -> None:
        self._settings = settings
        self._downloader = downloader

    @staticmethod
    def resolve_ticker(symbol: str, exchange: Exchange) -> str:
        normalized = symbol.strip().upper()
        if exchange == "NSE" and NSE_SYMBOL.fullmatch(normalized):
            return f"{normalized}.NS"
        if exchange == "BSE" and BSE_SECURITY_CODE.fullmatch(normalized):
            return f"{normalized}.BO"
        raise MarketDataUnavailableError(
            "A deterministic yfinance ticker is unavailable for this symbol and exchange"
        )

    async def get_daily_closes(
        self,
        symbol: str,
        exchange: Exchange,
        start_date: date,
        end_date: date,
    ) -> list[DailyClose]:
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
        if (end_date - start_date).days > 30:
            raise ValueError("market data window cannot exceed 30 days")
        ticker = self.resolve_ticker(symbol, exchange)
        for attempt in range(2):
            try:
                frame = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._downloader,
                        ticker,
                        start=start_date.isoformat(),
                        end=(end_date + timedelta(days=1)).isoformat(),
                        auto_adjust=False,
                        actions=False,
                        progress=False,
                        threads=False,
                        timeout=self._settings.market_data_timeout_seconds,
                    ),
                    timeout=self._settings.market_data_timeout_seconds,
                )
                return _frame_to_daily_closes(frame)
            except TimeoutError as error:
                if attempt == 1:
                    raise ProviderUnavailableError("Market-data request timed out") from error
            except MarketDataUnavailableError:
                raise
            except (KeyError, TypeError, ValueError, RuntimeError) as error:
                if attempt == 1:
                    raise ProviderUnavailableError("Market-data provider failed") from error
            await asyncio.sleep(0.2)
        raise ProviderUnavailableError("Market-data provider failed")


def _frame_to_daily_closes(frame: Any) -> list[DailyClose]:
    if not isinstance(frame, pd.DataFrame):
        raise ProviderUnavailableError("Market-data provider returned an unexpected result")
    if frame.empty:
        return []
    try:
        close_values = frame["Close"]
    except KeyError as error:
        raise ProviderUnavailableError("Market-data result has no close column") from error
    if isinstance(close_values, pd.DataFrame):
        if close_values.shape[1] != 1:
            raise ProviderUnavailableError("Market-data result contains ambiguous close columns")
        close_values = close_values.iloc[:, 0]
    closes: list[DailyClose] = []
    for index, raw_close in close_values.dropna().items():
        trading_date = pd.Timestamp(index).date()
        closes.append(DailyClose(trading_date=trading_date, close=float(raw_close)))
    closes.sort(key=lambda item: item.trading_date)
    return closes
