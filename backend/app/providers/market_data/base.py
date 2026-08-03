from datetime import date
from typing import Protocol, runtime_checkable

from app.schemas.domain import DailyClose, Exchange


@runtime_checkable
class MarketDataProvider(Protocol):
    async def get_daily_closes(
        self,
        symbol: str,
        exchange: Exchange,
        start_date: date,
        end_date: date,
    ) -> list[DailyClose]: ...
