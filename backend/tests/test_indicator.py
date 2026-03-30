from app.services.indicator import IndicatorService


def test_ma5_basic():
    prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    result = IndicatorService.calculate_ma(prices, 5)
    assert result[0] is None
    assert result[3] is None
    assert result[4] == 12.0
    assert result[5] == 13.0
    assert result[6] == 14.0

def test_ma20_needs_20_points():
    prices = [float(i) for i in range(25)]
    result = IndicatorService.calculate_ma(prices, 20)
    assert all(v is None for v in result[:19])
    assert result[19] == sum(range(20)) / 20

def test_ma_empty_list():
    assert IndicatorService.calculate_ma([], 5) == []

def test_ma_fewer_than_period():
    prices = [1.0, 2.0, 3.0]
    result = IndicatorService.calculate_ma(prices, 5)
    assert all(v is None for v in result)
    assert len(result) == 3


# --- 邊界測試 ---

def test_b7_6_all_close_identical():
    """全部 close 相同時，MA 應等於該 close 值"""
    prices = [100.0] * 10
    result = IndicatorService.calculate_ma(prices, 5)
    for v in result[4:]:
        assert v == 100.0


def test_b7_7_extreme_large_value():
    """極大值不應造成溢位"""
    prices = [999999.99] * 10
    result = IndicatorService.calculate_ma(prices, 5)
    for v in result[4:]:
        assert v == 999999.99


def test_b7_8_float_precision_rounded():
    """浮點精度：結果應 round 到小數 2 位"""
    prices = [0.1, 0.2, 0.3, 0.4, 0.5]
    result = IndicatorService.calculate_ma(prices, 5)
    assert result[4] == 0.3
    # 確認是精確的 0.3 而非 0.30000000000000004
    assert result[4] == round(sum(prices) / 5, 2)


def test_b7_5_49_data_points_ma20_last_30_non_null():
    """49 筆完整資料，MA20 最後 30 個應全部 non-null"""
    prices = [float(i) for i in range(49)]
    result = IndicatorService.calculate_ma(prices, 20)
    assert len(result) == 49
    last_30 = result[-30:]
    assert all(v is not None for v in last_30)


def test_b7_10_period_1():
    """period=1 時，每個值等於自身"""
    prices = [10.0, 20.0, 30.0, 40.0, 50.0]
    result = IndicatorService.calculate_ma(prices, 1)
    assert result == prices
