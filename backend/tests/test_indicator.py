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
