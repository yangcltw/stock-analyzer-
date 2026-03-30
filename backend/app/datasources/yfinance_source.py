import asyncio
from functools import partial

import yfinance as yf

from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData


class YFinanceSource(StockDataSource):
    def __init__(self):
        self._name_cache: dict[str, str] = {}

    _FETCH_TIMEOUT = 30  # seconds

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        loop = asyncio.get_running_loop()
        df = await asyncio.wait_for(
            loop.run_in_executor(None, partial(self._fetch, symbol, count)),
            timeout=self._FETCH_TIMEOUT,
        )

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

    def _get_yf_symbol(self, symbol: str) -> str:
        ticker_tw = yf.Ticker(f"{symbol}.TW")
        df = ticker_tw.history(period="5d")
        if not df.empty:
            return f"{symbol}.TW"
        return f"{symbol}.TWO"

    def _fetch(self, symbol: str, count: int):
        yf_symbol = self._get_yf_symbol(symbol)
        ticker = yf.Ticker(yf_symbol)
        return ticker.history(period=f"{count * 2}d").tail(count)

    def _fetch_name(self, symbol: str) -> str:
        yf_symbol = self._get_yf_symbol(symbol)
        ticker = yf.Ticker(yf_symbol)
        return ticker.info.get("longName", symbol)
