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
