from datetime import datetime
from zoneinfo import ZoneInfo

from app.utils.cache_ttl import get_ttl_seconds

TW = ZoneInfo("Asia/Taipei")


def test_ttl_during_trading_hours():
    now = datetime(2026, 3, 30, 10, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 12600

def test_ttl_after_close():
    now = datetime(2026, 3, 30, 14, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 68400

def test_ttl_friday_after_close():
    now = datetime(2026, 3, 27, 14, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 241200

def test_ttl_saturday():
    now = datetime(2026, 3, 28, 12, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 162000

def test_ttl_before_market_open():
    now = datetime(2026, 3, 30, 8, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 19800
