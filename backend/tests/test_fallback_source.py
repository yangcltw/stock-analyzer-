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


@pytest.mark.asyncio
async def test_primary_returns_empty_list_no_fallback():
    """BC-FB-05: Primary 回傳空列表（非異常）— 驗證不觸發 fallback，直接回傳空列表。"""
    primary = AsyncMock()
    primary.get_daily_data.return_value = []
    fallback = AsyncMock()

    source = FallbackDataSource(primary, fallback)
    result = await source.get_daily_data("2330", 5)

    assert result == []
    fallback.get_daily_data.assert_not_called()


@pytest.mark.asyncio
async def test_both_fail_raises_fallback_exception():
    """BC-FB-04: 兩者都失敗時，拋出的是 fallback 的異常（而非 primary）。"""
    primary = AsyncMock()
    primary.get_daily_data.side_effect = Exception("primary error")
    fallback = AsyncMock()
    fallback.get_daily_data.side_effect = ValueError("fallback error")

    source = FallbackDataSource(primary, fallback)
    with pytest.raises(ValueError, match="fallback error"):
        await source.get_daily_data("2330", 5)
