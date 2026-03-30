import pytest
from unittest.mock import AsyncMock, patch

from app.datasources.twse_source import TWSESource


def _mock_twse_response():
    """Mock TWSE STOCK_DAY API response.

    Real TWSE STOCK_DAY column order:
    [0] 日期, [1] 成交股數, [2] 成交金額, [3] 開盤價, [4] 最高價,
    [5] 最低價, [6] 收盤價, [7] 漲跌價差, [8] 成交筆數

    Note: 成交股數 ([1]) is in shares, not lots.
    """
    return {
        "stat": "OK",
        "data": [
            ["115/03/02", "35,185,922", "15,500,000,000", "890.00", "895.00", "885.00", "892.00", "+5.00", "12,345"],
            ["115/03/03", "40,210,388", "18,000,000,000", "892.00", "900.00", "890.00", "898.00", "+6.00", "15,678"],
        ],
    }


@pytest.mark.asyncio
async def test_twse_parses_response():
    source = TWSESource()

    with patch.object(source, "_fetch_month", new_callable=AsyncMock, return_value=_mock_twse_response()):
        result = await source.get_daily_data("2330", 2)

    assert len(result) == 2
    assert result[0].close == 892.0
    assert result[0].volume == 35185922


@pytest.mark.asyncio
async def test_twse_converts_roc_date():
    source = TWSESource()

    with patch.object(source, "_fetch_month", new_callable=AsyncMock, return_value=_mock_twse_response()):
        result = await source.get_daily_data("2330", 2)

    assert result[0].date == "2026-03-02"
