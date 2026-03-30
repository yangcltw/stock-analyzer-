from __future__ import annotations


class IndicatorService:
    @staticmethod
    def calculate_ma(prices: list[float], period: int) -> list[float | None]:
        result: list[float | None] = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(None)
            else:
                window = prices[i - period + 1 : i + 1]
                result.append(round(sum(window) / period, 2))
        return result
