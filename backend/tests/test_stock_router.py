import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.datasources.models import StockDailyData


def _make_data(n: int) -> list[StockDailyData]:
    return [
        StockDailyData(
            date=f"2026-03-{i+1:02d}",
            open=100.0+i, high=105.0+i, low=95.0+i,
            close=102.0+i, volume=1000*(i+1),
        )
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def clear_ai_cache():
    import app.routers.stock as stock_mod
    stock_mod._ai_cache.clear()


@pytest.fixture
def client():
    with patch("app.main.run_migrations", new_callable=AsyncMock), \
         patch("app.main.close_pool", new_callable=AsyncMock):
        from app.main import app
        with TestClient(app) as c:
            yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_stock_returns_30_days_with_full_ma(client):
    with patch("app.routers.stock.get_data_source") as mock_ds, \
         patch("app.routers.stock.get_ai_analyzer") as mock_ai, \
         patch("app.routers.stock.get_stock_name", new_callable=AsyncMock, return_value="台積電"):
        mock_ds.return_value = AsyncMock(get_daily_data=AsyncMock(return_value=_make_data(49)))
        mock_ai.return_value = AsyncMock(analyze=AsyncMock(return_value="趨勢分析"))

        resp = client.get("/api/stock/2330")

    body = resp.json()
    assert resp.status_code == 200
    assert body["symbol"] == "2330"
    assert body["name"] == "台積電"
    assert len(body["data"]) == 30
    assert len(body["ma5"]) == 30
    assert len(body["ma20"]) == 30
    assert all(v is not None for v in body["ma5"])
    assert all(v is not None for v in body["ma20"])
    assert body["ai_analysis"] == "趨勢分析"


def test_stock_graceful_without_ai(client):
    with patch("app.routers.stock.get_data_source") as mock_ds, \
         patch("app.routers.stock.get_ai_analyzer") as mock_ai, \
         patch("app.routers.stock.get_stock_name", new_callable=AsyncMock, return_value=None):
        mock_ds.return_value = AsyncMock(get_daily_data=AsyncMock(return_value=_make_data(49)))
        mock_ai.return_value = AsyncMock(analyze=AsyncMock(return_value=None))

        resp = client.get("/api/stock/2330")

    body = resp.json()
    assert resp.status_code == 200
    assert body["ai_analysis"] is None


def test_invalid_symbol_rejected(client):
    resp = client.get("/api/stock/AAPL")
    assert resp.status_code == 400
    assert "Invalid Taiwan stock symbol" in resp.json()["detail"]


def test_invalid_symbol_too_short(client):
    resp = client.get("/api/stock/12")
    assert resp.status_code == 400


def test_invalid_symbol_too_long(client):
    resp = client.get("/api/stock/1234567")
    assert resp.status_code == 400
