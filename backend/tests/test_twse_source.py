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


@pytest.mark.asyncio
async def test_twse_all_months_stat_not_ok():
    """BC-TW-04: TWSE stat 非 "OK" — mock 所有 3 個月份都回傳 stat != "OK"，驗證拋出 ValueError。"""
    source = TWSESource()
    bad_response = {"stat": "FAIL", "data": []}

    with patch.object(source, "_fetch_month", new_callable=AsyncMock, return_value=bad_response):
        with pytest.raises(ValueError, match="No data from TWSE"):
            await source.get_daily_data("2330", 5)


@pytest.mark.asyncio
async def test_twse_row_with_insufficient_fields_skipped():
    """BC-TW-05: 回傳欄位不足 — mock row 只有 5 個欄位，驗證被跳過不 crash。"""
    source = TWSESource()
    response_with_short_row = {
        "stat": "OK",
        "data": [
            ["115/03/02", "35,185,922", "15,500,000,000", "890.00", "895.00"],  # 只有 5 欄
            ["115/03/03", "40,210,388", "18,000,000,000", "892.00", "900.00", "890.00", "898.00", "+6.00", "15,678"],
        ],
    }
    no_data = {"stat": "OK", "data": []}

    with patch.object(
        source, "_fetch_month", new_callable=AsyncMock,
        side_effect=[response_with_short_row, no_data, no_data],
    ):
        result = await source.get_daily_data("2330", 2)

    # 欄位不足的 row 被跳過，只剩 1 筆
    assert len(result) == 1
    assert result[0].close == 898.0


@pytest.mark.asyncio
async def test_twse_fetch_month_returns_none():
    """BC-TW-07: HTTP 非 200 — mock _fetch_month 回傳 None，驗證所有月份都 None 時拋出 ValueError。"""
    source = TWSESource()

    with patch.object(source, "_fetch_month", new_callable=AsyncMock, return_value=None):
        with pytest.raises(ValueError, match="No data from TWSE"):
            await source.get_daily_data("2330", 5)


@pytest.mark.asyncio
async def test_twse_roc_cross_year_date():
    """BC-TW-02: 跨年日期 114/12/31 → 2025-12-31 — 驗證 ROC 跨年日期轉換正確。"""
    source = TWSESource()
    cross_year_response = {
        "stat": "OK",
        "data": [
            ["114/12/31", "30,000,000", "12,000,000,000", "880.00", "890.00", "875.00", "885.00", "+3.00", "10,000"],
        ],
    }

    with patch.object(source, "_fetch_month", new_callable=AsyncMock, return_value=cross_year_response):
        result = await source.get_daily_data("2330", 1)

    assert len(result) == 1
    assert result[0].date == "2025-12-31"
