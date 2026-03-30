import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from app.datasources.yfinance_source import YFinanceSource


def _mock_dataframe(n: int) -> pd.DataFrame:
    dates = pd.date_range("2026-03-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(n)],
            "High": [105.0 + i for i in range(n)],
            "Low": [95.0 + i for i in range(n)],
            "Close": [102.0 + i for i in range(n)],
            "Volume": [1000 * (i + 1) for i in range(n)],
        },
        index=dates,
    )


@pytest.mark.asyncio
async def test_yfinance_returns_stock_data():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_dataframe(5)

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        result = await source.get_daily_data("2330", 5)

    assert len(result) == 5
    assert result[0].open == 100.0
    assert result[0].close == 102.0


@pytest.mark.asyncio
async def test_yfinance_appends_tw_suffix():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_dataframe(5)

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker) as mock_cls:
        await source.get_daily_data("2330", 5)

    mock_cls.assert_called_once_with("2330.TW")


@pytest.mark.asyncio
async def test_yfinance_raises_on_empty_data():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(ValueError, match="No data"):
            await source.get_daily_data("9999", 5)


@pytest.mark.asyncio
async def test_yfinance_get_stock_name():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.info = {"longName": "Taiwan Semiconductor"}

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        name = await source.get_stock_name("2330")

    assert name == "Taiwan Semiconductor"


@pytest.mark.asyncio
async def test_yfinance_get_stock_name_fallback():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.info = {}

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        name = await source.get_stock_name("2330")

    assert name == "2330"


@pytest.mark.asyncio
async def test_yfinance_partial_data_fewer_than_requested():
    """BC-YF-05: API 回傳部分天數（< count）— 要求 49 筆但只拿到 20 筆，驗證回傳 20 筆不報錯。"""
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_dataframe(20)

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        result = await source.get_daily_data("2330", 49)

    assert len(result) == 20
    assert result[0].open == 100.0


@pytest.mark.asyncio
async def test_yfinance_dataframe_with_nan():
    """BC-YF-08: DataFrame 含 NaN — mock 含 NaN 的 DataFrame，驗證 float(NaN) 不報錯但產生 nan。"""
    import math

    source = YFinanceSource()
    mock_ticker = MagicMock()
    df = _mock_dataframe(3)
    df.iloc[1, df.columns.get_loc("Close")] = float("nan")
    mock_ticker.history.return_value = df

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        result = await source.get_daily_data("2330", 3)

    assert len(result) == 3
    assert math.isnan(result[1].close)


@pytest.mark.asyncio
async def test_yfinance_get_stock_name_info_raises():
    """BC-YF-09: get_stock_name 中 ticker.info 拋異常 — 驗證異常向上傳播。"""
    source = YFinanceSource()
    mock_ticker = MagicMock()
    type(mock_ticker).info = property(lambda self: (_ for _ in ()).throw(Exception("API error")))

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(Exception, match="API error"):
            await source.get_stock_name("2330")


@pytest.mark.asyncio
async def test_yfinance_etf_symbol_suffix():
    """BC-YF-02: ETF 代號 00878 — 驗證組合為 "00878.TW"。"""
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_dataframe(5)

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker) as mock_cls:
        await source.get_daily_data("00878", 5)

    mock_cls.assert_called_once_with("00878.TW")
