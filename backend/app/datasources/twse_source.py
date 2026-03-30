from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import httpx

from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData


class TWSESource(StockDataSource):
    """TWSE STOCK_DAY API data source.

    Real TWSE STOCK_DAY column order:
    [0] 日期, [1] 成交股數, [2] 成交金額, [3] 開盤價, [4] 最高價,
    [5] 最低價, [6] 收盤價, [7] 漲跌價差, [8] 成交筆數
    """

    BASE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        all_data: list[StockDailyData] = []
        current = date.today()

        for _ in range(3):
            resp = await self._fetch_month(symbol, current.year, current.month)
            if resp and resp.get("stat") == "OK" and resp.get("data"):
                parsed = self._parse_rows(resp["data"])
                all_data = parsed + all_data
            current = (current.replace(day=1) - timedelta(days=1))

        if not all_data:
            raise ValueError(f"No data from TWSE for symbol {symbol}")

        return all_data[-count:]

    async def _fetch_month(self, symbol: str, year: int, month: int) -> dict | None:
        date_str = f"{year}{month:02d}01"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.BASE_URL,
                    params={"response": "json", "date": date_str, "stockNo": symbol},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return resp.json()
        except (httpx.TimeoutException, httpx.ConnectError):
            pass
        return None

    def _parse_rows(self, rows: list[list[str]]) -> list[StockDailyData]:
        result = []
        for row in rows:
            try:
                parts = row[0].strip().split("/")
                y = int(parts[0]) + 1911
                m = int(parts[1])
                d = int(parts[2])

                volume = int(row[1].replace(",", ""))

                result.append(StockDailyData(
                    date=f"{y}-{m:02d}-{d:02d}",
                    open=float(row[3].replace(",", "")),
                    high=float(row[4].replace(",", "")),
                    low=float(row[5].replace(",", "")),
                    close=float(row[6].replace(",", "")),
                    volume=volume,
                ))
            except (ValueError, IndexError):
                continue
        return result
