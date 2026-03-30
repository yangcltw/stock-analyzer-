import asyncio
import logging
from functools import partial

import yfinance as yf

from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData

logger = logging.getLogger(__name__)


class YFinanceSource(StockDataSource):
    """yfinance data source for Taiwan stocks.

    yfinance >= 1.2.0 uses curl_cffi to impersonate Chrome,
    handling cookies/crumb automatically. No custom session needed.
    """

    _FETCH_TIMEOUT = 30

    def __init__(self):
        self._name_cache: dict[str, str] = {}

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

    def _fetch(self, symbol: str, count: int):
        ticker = yf.Ticker(f"{symbol}.TW")
        df = ticker.history(period=f"{count * 2}d")

        if df.empty:
            logger.info(f"{symbol}.TW returned empty, trying .TWO")
            ticker = yf.Ticker(f"{symbol}.TWO")
            df = ticker.history(period=f"{count * 2}d")

        return df.tail(count)

    def _fetch_name(self, symbol: str) -> str:
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            name = ticker.info.get("longName") or ticker.info.get("shortName")
            if name:
                return name
        except Exception:
            pass
        return symbol
