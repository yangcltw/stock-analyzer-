from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from app.datasources.interface import StockDataSource
from app.datasources.yfinance_source import YFinanceSource
from app.datasources.twse_source import TWSESource
from app.datasources.fallback_source import FallbackDataSource
from app.datasources.db_source import DatabaseDataSource
from app.datasources.cached_source import CachedDataSource
from app.services.indicator import IndicatorService
from app.services.ai_analyzer import AIAnalyzer, GeminiAnalyzer, OpenAIAnalyzer, FallbackAIAnalyzer
from app.utils.cache_ttl import get_ttl_seconds

router = APIRouter(prefix="/api")

DISPLAY_DAYS = 30
LOOKBACK_DAYS = 19
FETCH_DAYS = DISPLAY_DAYS + LOOKBACK_DAYS  # 49

_data_source: StockDataSource | None = None
_yfinance_source: YFinanceSource | None = None
_ai_analyzer: AIAnalyzer | None = None

# AI analysis cache: symbol -> (analysis_text, expires_at)
_ai_cache: dict[str, tuple[str | None, float]] = {}


def get_data_source() -> StockDataSource:
    global _data_source, _yfinance_source
    if _data_source is None:
        _yfinance_source = YFinanceSource()
        twse = TWSESource()
        fallback = FallbackDataSource(_yfinance_source, twse)
        db = DatabaseDataSource(fallback)
        _data_source = CachedDataSource(db)
    return _data_source


def get_ai_analyzer() -> AIAnalyzer:
    global _ai_analyzer
    if _ai_analyzer is None:
        gemini = GeminiAnalyzer()
        openai = OpenAIAnalyzer()
        _ai_analyzer = FallbackAIAnalyzer(gemini, openai)
    return _ai_analyzer


async def get_stock_name(symbol: str) -> str | None:
    global _yfinance_source
    if _yfinance_source is None:
        _yfinance_source = YFinanceSource()
    try:
        return await _yfinance_source.get_stock_name(symbol)
    except Exception:
        return None


@router.get("/stock/{symbol}")
async def get_stock(symbol: str):
    if not symbol.isdigit() or not (3 <= len(symbol) <= 6):
        raise HTTPException(status_code=400, detail="Invalid Taiwan stock symbol")

    source = get_data_source()
    analyzer = get_ai_analyzer()

    try:
        all_data = await source.get_daily_data(symbol, FETCH_DAYS)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data source error: {str(e)}")

    if len(all_data) < DISPLAY_DAYS:
        raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

    all_closes = [d.close for d in all_data]
    all_ma5 = IndicatorService.calculate_ma(all_closes, 5)
    all_ma20 = IndicatorService.calculate_ma(all_closes, 20)

    display_data = all_data[-DISPLAY_DAYS:]
    display_ma5 = all_ma5[-DISPLAY_DAYS:]
    display_ma20 = all_ma20[-DISPLAY_DAYS:]

    # AI analysis with independent cache
    ai_result = None
    now = time.time()
    if symbol in _ai_cache:
        cached_ai, ai_expires_at = _ai_cache[symbol]
        if now < ai_expires_at:
            ai_result = cached_ai
    if ai_result is None:
        try:
            ai_result = await analyzer.analyze(symbol, display_data, display_ma5, display_ma20)
        except Exception:
            ai_result = None
        ttl = get_ttl_seconds()
        _ai_cache[symbol] = (ai_result, now + ttl)

    name = await get_stock_name(symbol)

    return {
        "symbol": symbol,
        "name": name,
        "data": [
            {"date": d.date, "open": d.open, "high": d.high, "low": d.low, "close": d.close, "volume": d.volume}
            for d in display_data
        ],
        "ma5": display_ma5,
        "ma20": display_ma20,
        "ai_analysis": ai_result,
    }
