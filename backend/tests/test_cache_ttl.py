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


# --- 邊界測試 ---

def test_b5_2_one_minute_before_close():
    """13:29 查詢 — 收盤前 1 分鐘，TTL = 60 秒"""
    now = datetime(2026, 3, 30, 13, 29, tzinfo=TW)
    assert get_ttl_seconds(now) == 60


def test_b5_3_exactly_at_close():
    """13:30 查詢 — 剛好收盤，TTL 到次交易日 09:00"""
    now = datetime(2026, 3, 30, 13, 30, tzinfo=TW)
    # 13:30 已不小於 market_close，所以走 next_trading_day_open
    # 次交易日 2026-03-31 09:00 距離 13:30 = 19.5 小時 = 70200 秒
    assert get_ttl_seconds(now) == 70200


def test_b5_4_one_minute_after_close():
    """13:31 查詢 — 收盤後 1 分鐘，TTL 到次交易日 09:00"""
    now = datetime(2026, 3, 30, 13, 31, tzinfo=TW)
    # 次交易日 2026-03-31 09:00 距離 13:31 = 19 小時 29 分 = 70140 秒
    assert get_ttl_seconds(now) == 70140
