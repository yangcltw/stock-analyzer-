from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData


class FallbackDataSource(StockDataSource):
    def __init__(self, primary: StockDataSource, fallback: StockDataSource):
        self._primary = primary
        self._fallback = fallback

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        try:
            return await self._primary.get_daily_data(symbol, count)
        except Exception:
            return await self._fallback.get_daily_data(symbol, count)
