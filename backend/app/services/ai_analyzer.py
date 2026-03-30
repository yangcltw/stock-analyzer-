from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.config import settings
from app.datasources.models import StockDailyData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一位台股技術分析助手。請根據提供的實際股價數據和均線數據，"
    "用繁體中文描述股價趨勢。你必須：\n"
    "1. 只根據實際數據描述趨勢\n"
    "2. 絕對不可以提供任何投資建議\n"
    "3. 不可以建議買入、賣出或持有\n"
    "4. 回覆限制在 200 字以內"
)


def _build_user_prompt(symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]) -> str:
    prices_text = "\n".join(
        f"{d.date}: 開={d.open} 高={d.high} 低={d.low} 收={d.close} 量={d.volume}"
        for d in data
    )
    ma_text = (
        f"MA5 最新值: {ma5[-1]}, MA20 最新值: {ma20[-1]}\n"
        f"MA5 趨勢: {ma5[-5:]}\nMA20 趨勢: {ma20[-5:]}"
    )
    return f"股票代號: {symbol}\n\n近期股價資料:\n{prices_text}\n\n均線資料:\n{ma_text}"


class AIAnalyzer(ABC):
    @abstractmethod
    async def analyze(
        self, symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]
    ) -> str | None:
        ...


class GeminiStreamAnalyzer:
    """Separate class for streaming — used directly by SSE endpoint."""
    pass


class GeminiAnalyzer(AIAnalyzer):
    def __init__(self):
        from google import genai
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def analyze(
        self, symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]
    ) -> str | None:
        try:
            from google.genai import types
            user_prompt = _build_user_prompt(symbol, data, ma5, ma20)
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.3,
                    max_output_tokens=1000,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
                contents=user_prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return None


class OpenAIAnalyzer(AIAnalyzer):
    def __init__(self):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(
        self, symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]
    ) -> str | None:
        try:
            user_prompt = _build_user_prompt(symbol, data, ma5, ma20)
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            return None


class FallbackAIAnalyzer(AIAnalyzer):
    """Try primary analyzer first, fallback to secondary on failure."""

    def __init__(self, primary: AIAnalyzer, secondary: AIAnalyzer):
        self._primary = primary
        self._secondary = secondary

    async def analyze(
        self, symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]
    ) -> str | None:
        result = await self._primary.analyze(symbol, data, ma5, ma20)
        if result is not None:
            return result
        return await self._secondary.analyze(symbol, data, ma5, ma20)
