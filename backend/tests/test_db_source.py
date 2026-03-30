import pytest
from unittest.mock import AsyncMock

from app.datasources.models import StockDailyData
from app.datasources.db_source import DatabaseDataSource


def _make_data(n: int) -> list[StockDailyData]:
    return [
        StockDailyData(
            date=f"2026-03-{i+1:02d}", open=100.0+i, high=105.0+i,
            low=95.0+i, close=102.0+i, volume=1000*(i+1),
        )
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_delegates_to_upstream_when_db_fresh_empty(monkeypatch):
    upstream = AsyncMock()
    upstream.get_daily_data.return_value = _make_data(5)
    source = DatabaseDataSource(upstream)

    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_read_stale_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_write_to_db", AsyncMock())
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 5
    upstream.get_daily_data.assert_called_once()


@pytest.mark.asyncio
async def test_returns_fresh_db_data_when_sufficient(monkeypatch):
    upstream = AsyncMock()
    source = DatabaseDataSource(upstream)

    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=_make_data(5)))
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 5
    upstream.get_daily_data.assert_not_called()


@pytest.mark.asyncio
async def test_returns_stale_db_data_when_upstream_fails(monkeypatch):
    upstream = AsyncMock()
    upstream.get_daily_data.side_effect = Exception("all APIs down")
    source = DatabaseDataSource(upstream)

    stale = _make_data(3)
    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_read_stale_from_db", AsyncMock(return_value=stale))
    monkeypatch.setattr(source, "_write_to_db", AsyncMock())
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_fresh_path_uses_freshness_filter(monkeypatch):
    upstream = AsyncMock()
    source = DatabaseDataSource(upstream)

    fresh_mock = AsyncMock(return_value=_make_data(5))
    stale_mock = AsyncMock(return_value=_make_data(5))
    monkeypatch.setattr(source, "_read_fresh_from_db", fresh_mock)
    monkeypatch.setattr(source, "_read_stale_from_db", stale_mock)
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 5
    fresh_mock.assert_called_once()
    stale_mock.assert_not_called()


@pytest.mark.asyncio
async def test_upstream_fails_stale_data_fewer_than_count(monkeypatch):
    """BC-DB-06: Upstream 失敗，stale 資料不足 count — 驗證回傳部分資料。"""
    upstream = AsyncMock()
    upstream.get_daily_data.side_effect = Exception("upstream down")
    source = DatabaseDataSource(upstream)

    stale = _make_data(2)
    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_read_stale_from_db", AsyncMock(return_value=stale))
    monkeypatch.setattr(source, "_write_to_db", AsyncMock())
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_upstream_fails_stale_empty_reraises(monkeypatch):
    """BC-DB-05: Upstream 失敗且 stale 為空 — 驗證重新拋出 upstream 異常。"""
    upstream = AsyncMock()
    upstream.get_daily_data.side_effect = Exception("upstream exploded")
    source = DatabaseDataSource(upstream)

    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_read_stale_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_write_to_db", AsyncMock())
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    with pytest.raises(Exception, match="upstream exploded"):
        await source.get_daily_data("2330", 5)


@pytest.mark.asyncio
async def test_fresh_db_exactly_equals_count_no_upstream(monkeypatch):
    """BC-DB-02: DB 資料剛好 = count — 驗證不呼叫 upstream。"""
    upstream = AsyncMock()
    source = DatabaseDataSource(upstream)

    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=_make_data(5)))
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 5
    upstream.get_daily_data.assert_not_called()
