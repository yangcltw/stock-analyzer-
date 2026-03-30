import pytest
from unittest.mock import AsyncMock

from app.datasources.models import StockDailyData
from app.datasources.fallback_source import FallbackDataSource


def _make_data(n: int) -> list[StockDailyData]:
    return [
        StockDailyData(date=f"2026-03-{i+1:02d}", open=100.0, high=105.0, low=95.0, close=102.0, volume=1000)
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_uses_primary_when_available():
    primary = AsyncMock()
    primary.get_daily_data.return_value = _make_data(5)
    fallback = AsyncMock()

    source = FallbackDataSource(primary, fallback)
    result = await source.get_daily_data("2330", 5)

    assert len(result) == 5
    fallback.get_daily_data.assert_not_called()


@pytest.mark.asyncio
async def test_switches_on_primary_error():
    primary = AsyncMock()
    primary.get_daily_data.side_effect = Exception("yfinance down")
    fallback = AsyncMock()
    fallback.get_daily_data.return_value = _make_data(5)

    source = FallbackDataSource(primary, fallback)
    result = await source.get_daily_data("2330", 5)

    assert len(result) == 5
    fallback.get_daily_data.assert_called_once()


@pytest.mark.asyncio
async def test_raises_when_all_fail():
    primary = AsyncMock()
    primary.get_daily_data.side_effect = Exception("yfinance down")
    fallback = AsyncMock()
    fallback.get_daily_data.side_effect = Exception("TWSE down")

    source = FallbackDataSource(primary, fallback)
    with pytest.raises(Exception, match="TWSE down"):
        await source.get_daily_data("2330", 5)
