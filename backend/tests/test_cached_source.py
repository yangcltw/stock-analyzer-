import pytest
from unittest.mock import AsyncMock, patch

from app.datasources.models import StockDailyData
from app.datasources.cached_source import CachedDataSource


def _make_data(n: int) -> list[StockDailyData]:
    return [
        StockDailyData(date=f"2026-03-{i+1:02d}", open=100.0, high=105.0, low=95.0, close=102.0, volume=1000)
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_returns_cache_on_second_call():
    upstream = AsyncMock()
    upstream.get_daily_data.return_value = _make_data(5)

    with patch("app.datasources.cached_source.get_ttl_seconds", return_value=3600):
        source = CachedDataSource(upstream)
        await source.get_daily_data("2330", 5)
        await source.get_daily_data("2330", 5)

    upstream.get_daily_data.assert_called_once()


@pytest.mark.asyncio
async def test_different_symbols_not_shared():
    upstream = AsyncMock()
    upstream.get_daily_data.return_value = _make_data(5)

    with patch("app.datasources.cached_source.get_ttl_seconds", return_value=3600):
        source = CachedDataSource(upstream)
        await source.get_daily_data("2330", 5)
        await source.get_daily_data("2317", 5)

    assert upstream.get_daily_data.call_count == 2


@pytest.mark.asyncio
async def test_cache_expires_after_ttl():
    """Verify that upstream is called again after TTL expires."""
    upstream = AsyncMock()
    upstream.get_daily_data.return_value = _make_data(5)

    fake_time = [1000.0]

    def mock_time():
        return fake_time[0]

    with patch("app.datasources.cached_source.get_ttl_seconds", return_value=60), \
         patch("app.datasources.cached_source.time") as mock_time_module:
        mock_time_module.time = mock_time

        source = CachedDataSource(upstream)

        # First call — fetches from upstream
        await source.get_daily_data("2330", 5)
        assert upstream.get_daily_data.call_count == 1

        # Second call — still within TTL, should use cache
        fake_time[0] = 1050.0
        await source.get_daily_data("2330", 5)
        assert upstream.get_daily_data.call_count == 1

        # Third call — past TTL (1000 + 60 = 1060), should fetch again
        fake_time[0] = 1070.0
        await source.get_daily_data("2330", 5)
        assert upstream.get_daily_data.call_count == 2


# --- 邊界測試 ---

@pytest.mark.asyncio
async def test_b6_1_concurrent_dedup():
    """並發 dedup：同時 10 個請求同一 symbol，upstream 只被呼叫 1 次"""
    import asyncio

    call_count = 0

    async def slow_upstream(symbol, count):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return _make_data(count)

    upstream = AsyncMock()
    upstream.get_daily_data = slow_upstream

    with patch("app.datasources.cached_source.get_ttl_seconds", return_value=3600):
        source = CachedDataSource(upstream)
        tasks = [source.get_daily_data("2330", 5) for _ in range(10)]
        results = await asyncio.gather(*tasks)

    assert call_count == 1
    assert all(len(r) == 5 for r in results)


@pytest.mark.asyncio
async def test_b6_2_different_symbols_no_interlock():
    """不同 symbol 不互鎖：同時請求 "2330" 和 "2317"，各呼叫 1 次"""
    import asyncio

    call_symbols = []

    async def tracking_upstream(symbol, count):
        call_symbols.append(symbol)
        await asyncio.sleep(0.05)
        return _make_data(count)

    upstream = AsyncMock()
    upstream.get_daily_data = tracking_upstream

    with patch("app.datasources.cached_source.get_ttl_seconds", return_value=3600):
        source = CachedDataSource(upstream)
        await asyncio.gather(
            source.get_daily_data("2330", 5),
            source.get_daily_data("2317", 5),
        )

    assert call_symbols.count("2330") == 1
    assert call_symbols.count("2317") == 1
