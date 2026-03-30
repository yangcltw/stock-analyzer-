from datetime import datetime, date
from zoneinfo import ZoneInfo

from app.utils.trading_calendar import is_trading_day, get_next_trading_day_open

TW = ZoneInfo("Asia/Taipei")


def test_weekday_is_trading_day():
    assert is_trading_day(date(2026, 3, 30)) is True

def test_saturday_is_not_trading_day():
    assert is_trading_day(date(2026, 3, 28)) is False

def test_sunday_is_not_trading_day():
    assert is_trading_day(date(2026, 3, 29)) is False

def test_holiday_is_not_trading_day():
    assert is_trading_day(date(2026, 1, 1)) is False

def test_next_trading_day_from_friday_afternoon():
    now = datetime(2026, 3, 27, 14, 0, tzinfo=TW)
    result = get_next_trading_day_open(now)
    assert result == datetime(2026, 3, 30, 9, 0, tzinfo=TW)

def test_next_trading_day_from_weekday_morning():
    now = datetime(2026, 3, 30, 10, 0, tzinfo=TW)
    result = get_next_trading_day_open(now)
    assert result == datetime(2026, 3, 31, 9, 0, tzinfo=TW)

def test_next_trading_day_from_saturday():
    now = datetime(2026, 3, 28, 12, 0, tzinfo=TW)
    result = get_next_trading_day_open(now)
    assert result == datetime(2026, 3, 30, 9, 0, tzinfo=TW)
