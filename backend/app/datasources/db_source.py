from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData
from app.db.connection import get_pool


class DatabaseDataSource(StockDataSource):
    def __init__(self, upstream: StockDataSource, freshness_hours: int = 24):
        self._upstream = upstream
        self._freshness_hours = freshness_hours

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        pool = await get_pool()

        rows = await self._read_fresh_from_db(pool, symbol, count)
        if len(rows) >= count:
            return rows[:count]

        try:
            data = await self._upstream.get_daily_data(symbol, count)
            await self._write_to_db(pool, symbol, data)
            return data
        except Exception:
            stale_rows = await self._read_stale_from_db(pool, symbol, count)
            if stale_rows:
                return stale_rows
            raise

    async def _read_fresh_from_db(self, pool, symbol: str, count: int) -> list[StockDailyData]:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT date, open, high, low, close, volume
                FROM stock_daily_data
                WHERE symbol = $1
                  AND fetched_at > NOW() - INTERVAL '1 hour' * $3
                ORDER BY date DESC
                LIMIT $2
                """,
                symbol, count, self._freshness_hours
            )
        return [
            StockDailyData(
                date=row["date"].isoformat(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )
            for row in reversed(rows)
        ]

    async def _read_stale_from_db(self, pool, symbol: str, count: int) -> list[StockDailyData]:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT date, open, high, low, close, volume
                FROM stock_daily_data
                WHERE symbol = $1
                ORDER BY date DESC
                LIMIT $2
                """,
                symbol, count
            )
        return [
            StockDailyData(
                date=row["date"].isoformat(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )
            for row in reversed(rows)
        ]

    async def _write_to_db(self, pool, symbol: str, data: list[StockDailyData]):
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO stock_daily_data (symbol, date, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    open = EXCLUDED.open, high = EXCLUDED.high,
                    low = EXCLUDED.low, close = EXCLUDED.close,
                    volume = EXCLUDED.volume, fetched_at = NOW()
                """,
                [(symbol, d.date, d.open, d.high, d.low, d.close, d.volume) for d in data],
            )
