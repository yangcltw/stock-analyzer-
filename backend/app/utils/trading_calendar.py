from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TW_TZ = ZoneInfo("Asia/Taipei")

logger = logging.getLogger(__name__)

_holidays: set[date] | None = None


def _load_holidays() -> set[date]:
    global _holidays
    if _holidays is not None:
        return _holidays
    holidays_dir = Path(__file__).parent.parent.parent / "holidays"
    _holidays = set()
    for json_file in holidays_dir.glob("*.json"):
        with open(json_file) as f:
            dates = json.load(f)
            _holidays.update(date.fromisoformat(d) for d in dates)

    current_year = date.today().year
    if not any(d.year == current_year for d in _holidays):
        logger.warning(
            f"No holiday data for {current_year}. "
            "All weekdays will be treated as trading days."
        )

    return _holidays


def is_trading_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d not in _load_holidays()


def get_next_trading_day_open(now: datetime) -> datetime:
    current = now.astimezone(TW_TZ).date() + timedelta(days=1)
    while not is_trading_day(current):
        current += timedelta(days=1)
    return datetime(current.year, current.month, current.day, 9, 0, tzinfo=TW_TZ)
