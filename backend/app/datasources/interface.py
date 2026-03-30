from abc import ABC, abstractmethod

from app.datasources.models import StockDailyData


class StockDataSource(ABC):
    @abstractmethod
    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        """Fetch daily stock data.

        Args:
            symbol: Taiwan stock symbol (digits only, e.g. "2330").
            count: Number of trading day rows to return.
        """
        ...
