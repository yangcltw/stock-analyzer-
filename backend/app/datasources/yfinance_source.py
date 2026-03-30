import asyncio
from functools import partial

import yfinance as yf

from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData


class YFinanceSource(StockDataSource):
    def __init__(self):
        self._name_cache: dict[str, str] = {}

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        loop = asyncio.get_running_loop()
        # TODO(high): wrap with asyncio.wait_for to prevent hanging on network issues
        df = await loop.run_in_executor(None, partial(self._fetch, symbol, count))

        if df.empty:
            raise ValueError(f"No data returned for symbol {symbol}")

        return [
            StockDailyData(
                date=index.strftime("%Y-%m-%d"),
                open=round(float(row["Open"]), 2),
                high=round(float(row["High"]), 2),
                low=round(float(row["Low"]), 2),
                close=round(float(row["Close"]), 2),
                volume=int(row["Volume"]),
            )
            for index, row in df.iterrows()
        ]

    async def get_stock_name(self, symbol: str) -> str:
        if symbol in self._name_cache:
            return self._name_cache[symbol]

        loop = asyncio.get_running_loop()
        name = await loop.run_in_executor(None, partial(self._fetch_name, symbol))
        self._name_cache[symbol] = name
        return name

    def _fetch(self, symbol: str, count: int):
        # TODO(high): .TW hardcoded — OTC stocks need .TWO suffix, decide scope
        ticker = yf.Ticker(f"{symbol}.TW")
        return ticker.history(period=f"{count * 2}d").tail(count)

    def _fetch_name(self, symbol: str) -> str:
        ticker = yf.Ticker(f"{symbol}.TW")
        return ticker.info.get("longName", symbol)
