import asyncio
import time

from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData
from app.utils.cache_ttl import get_ttl_seconds


class CachedDataSource(StockDataSource):
    def __init__(self, upstream: StockDataSource):
        self._upstream = upstream
        self._cache: dict[str, tuple[list[StockDailyData], float]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        cache_key = f"{symbol}_{count}"

        if cache_key in self._cache:
            data, expires_at = self._cache[cache_key]
            if time.time() < expires_at:
                return data

        # Use setdefault which is atomic in CPython — avoids race on lock creation
        lock = self._locks.setdefault(cache_key, asyncio.Lock())

        async with lock:
            # Double-check after acquiring lock
            if cache_key in self._cache:
                data, expires_at = self._cache[cache_key]
                if time.time() < expires_at:
                    return data

            data = await self._upstream.get_daily_data(symbol, count)
            ttl = get_ttl_seconds()
            self._cache[cache_key] = (data, time.time() + ttl)
            return data
