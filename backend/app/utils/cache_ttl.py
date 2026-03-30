from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.utils.trading_calendar import TW_TZ, is_trading_day, get_next_trading_day_open

MARKET_CLOSE_HOUR = 13
MARKET_CLOSE_MINUTE = 30


def get_ttl_seconds(now: datetime | None = None) -> int:
    if now is None:
        now = datetime.now(TW_TZ)
    else:
        now = now.astimezone(TW_TZ)

    today = now.date()

    if is_trading_day(today):
        market_close = now.replace(
            hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE,
            second=0, microsecond=0
        )
        if now < market_close:
            return int((market_close - now).total_seconds())

    next_open = get_next_trading_day_open(now)
    return int((next_open - now).total_seconds())
