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


# --- 邊界測試 ---

def test_b8_3_special_chars_script_tag(client):
    """含特殊字元 <script> 的 symbol 應回傳 400"""
    resp = client.get("/api/stock/<script>")
    assert resp.status_code == 400


def test_b8_5_超長_symbol_256_chars(client):
    """超長 symbol（256 字元）應回傳 400"""
    long_symbol = "1" * 256
    resp = client.get(f"/api/stock/{long_symbol}")
    assert resp.status_code == 400


def test_b8_6_whitespace_only_symbol(client):
    """全空白 symbol 應回傳 400 或被 trim 後視為無效"""
    resp = client.get("/api/stock/   ")
    # FastAPI 路由會 trim 或 404，但即使到 handler 也不應通過驗證
    assert resp.status_code in (400, 404)


def test_b8_8_etf_0050_accepted(client):
    """ETF 代號 0050 應能正常處理，不被 symbol 驗證擋掉"""
    with patch("app.routers.stock.get_data_source") as mock_ds, \
         patch("app.routers.stock.get_ai_analyzer") as mock_ai, \
         patch("app.routers.stock.get_stock_name", new_callable=AsyncMock, return_value="元大台灣50"):
        mock_ds.return_value = AsyncMock(get_daily_data=AsyncMock(return_value=_make_data(49)))
        mock_ai.return_value = AsyncMock(analyze=AsyncMock(return_value="ETF 分析"))

        resp = client.get("/api/stock/0050")

    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "0050"
    assert body["name"] == "元大台灣50"


def test_b8_10_path_traversal_rejected(client):
    """Path traversal 攻擊應被拒絕（400 或 404 皆為安全行為）"""
    resp = client.get("/api/stock/..%2F..%2Fetc")
    assert resp.status_code in (400, 404)


def test_b9_1_graceful_degradation_ai_exception(client):
    """AI 分析拋出例外時，router 應 graceful degradation：回傳 200 + ai_analysis=None。"""
    with patch("app.routers.stock.get_data_source") as mock_ds, \
         patch("app.routers.stock.get_ai_analyzer") as mock_ai, \
         patch("app.routers.stock.get_stock_name", new_callable=AsyncMock, return_value="台積電"):
        mock_ds.return_value = AsyncMock(get_daily_data=AsyncMock(return_value=_make_data(49)))
        mock_ai.return_value = AsyncMock(analyze=AsyncMock(side_effect=Exception("OpenAI down")))

        resp = client.get("/api/stock/2330")

    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_analysis"] is None
    assert len(body["data"]) == 30


def test_data_source_error_returns_502(client):
    """Data source 發生錯誤應回傳 502"""
    with patch("app.routers.stock.get_data_source") as mock_ds:
        mock_ds.return_value = AsyncMock(
            get_daily_data=AsyncMock(side_effect=RuntimeError("Connection failed"))
        )

        resp = client.get("/api/stock/2330")

    assert resp.status_code == 502
    assert "Data source error" in resp.json()["detail"]
