from dataclasses import dataclass


@dataclass
class StockDailyData:
    date: str       # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int
