from __future__ import annotations

from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from app.config import settings
from app.datasources.models import StockDailyData


class AIAnalyzer(ABC):
    @abstractmethod
    async def analyze(
        self, symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]
    ) -> str | None:
        ...


class OpenAIAnalyzer(AIAnalyzer):
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(
        self, symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]
    ) -> str | None:
        try:
            prices_text = "\n".join(
                f"{d.date}: 開={d.open} 高={d.high} 低={d.low} 收={d.close} 量={d.volume}"
                for d in data
            )
            ma_text = (
                f"MA5 最新值: {ma5[-1]}, MA20 最新值: {ma20[-1]}\n"
                f"MA5 趨勢: {ma5[-5:]}\nMA20 趨勢: {ma20[-5:]}"
            )

            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一位台股技術分析助手。請根據提供的實際股價數據和均線數據，"
                            "用繁體中文描述股價趨勢。你必須：\n"
                            "1. 只根據實際數據描述趨勢\n"
                            "2. 絕對不可以提供任何投資建議\n"
                            "3. 不可以建議買入、賣出或持有\n"
                            "4. 回覆限制在 200 字以內"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"股票代號: {symbol}\n\n近期股價資料:\n{prices_text}\n\n均線資料:\n{ma_text}",
                    },
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content
        except Exception:
            return None
