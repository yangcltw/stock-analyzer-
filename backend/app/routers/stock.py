from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.datasources.interface import StockDataSource
from app.datasources.yfinance_source import YFinanceSource
from app.datasources.twse_source import TWSESource
from app.datasources.fallback_source import FallbackDataSource
from app.datasources.db_source import DatabaseDataSource
from app.datasources.cached_source import CachedDataSource
from app.services.indicator import IndicatorService
from app.services.ai_analyzer import GeminiStreamAnalyzer, OpenAIAnalyzer, FallbackAIAnalyzer, SYSTEM_PROMPT, _build_user_prompt
from app.utils.cache_ttl import get_ttl_seconds
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

DISPLAY_DAYS = 30
LOOKBACK_DAYS = 19
FETCH_DAYS = DISPLAY_DAYS + LOOKBACK_DAYS  # 49

_data_source: StockDataSource | None = None
_yfinance_source: YFinanceSource | None = None

# AI analysis cache: symbol -> (analysis_text, expires_at)
_ai_cache: dict[str, tuple[str, float]] = {}

SSE_TIMEOUT = 30  # seconds — kill SSE connection if AI takes longer


def get_data_source() -> StockDataSource:
    global _data_source, _yfinance_source
    if _data_source is None:
        _yfinance_source = YFinanceSource()
        twse = TWSESource()
        fallback = FallbackDataSource(_yfinance_source, twse)
        db = DatabaseDataSource(fallback)
        _data_source = CachedDataSource(db)
    return _data_source


async def get_stock_name(symbol: str) -> str | None:
    global _yfinance_source
    if _yfinance_source is None:
        _yfinance_source = YFinanceSource()
    try:
        return await _yfinance_source.get_stock_name(symbol)
    except Exception:
        return None


def _validate_symbol(symbol: str):
    if not symbol.isdigit() or not (3 <= len(symbol) <= 6):
        raise HTTPException(status_code=400, detail="Invalid Taiwan stock symbol")


async def _get_stock_data(symbol: str):
    """Shared logic: fetch data, calculate MA, return structured result."""
    source = get_data_source()

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
    }, display_data, display_ma5, display_ma20


@router.get("/stock/{symbol}")
async def get_stock(symbol: str):
    """Return stock data + MA immediately. No AI — use /stock/{symbol}/ai for SSE streaming."""
    _validate_symbol(symbol)
    result, _, _, _ = await _get_stock_data(symbol)
    return result


@router.get("/stock/{symbol}/ai")
async def get_stock_ai_stream(symbol: str, request: Request):
    """SSE endpoint: stream AI analysis token by token.

    Event types:
    - event: token   → data: {"text": "partial text"}
    - event: done    → data: {"text": "full text"}
    - event: cached  → data: {"text": "full text from cache"}
    - event: error   → data: {"message": "error description"}

    Connection management:
    - Checks client disconnect before each send
    - Timeout after SSE_TIMEOUT seconds
    - Proper cleanup on any exception
    """
    _validate_symbol(symbol)

    async def event_stream():
        try:
            # Check cache first
            now = time.time()
            if symbol in _ai_cache:
                cached_text, expires_at = _ai_cache[symbol]
                if now < expires_at:
                    yield f"event: cached\ndata: {json.dumps({'text': cached_text}, ensure_ascii=False)}\n\n"
                    return

            # Need to fetch stock data for AI prompt
            try:
                result, display_data, display_ma5, display_ma20 = await _get_stock_data(symbol)
            except HTTPException as e:
                yield f"event: error\ndata: {json.dumps({'message': e.detail})}\n\n"
                return

            # Stream from Gemini
            full_text = ""
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.gemini_api_key)
                user_prompt = _build_user_prompt(symbol, display_data, display_ma5, display_ma20)

                stream = client.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.3,
                        max_output_tokens=1000,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                    contents=user_prompt,
                )

                start_time = time.time()
                for chunk in stream:
                    # Timeout check
                    if time.time() - start_time > SSE_TIMEOUT:
                        logger.warning(f"SSE timeout for {symbol} after {SSE_TIMEOUT}s")
                        break

                    # Client disconnect check
                    if await request.is_disconnected():
                        logger.info(f"SSE client disconnected for {symbol}")
                        return

                    if chunk.text:
                        full_text += chunk.text
                        yield f"event: token\ndata: {json.dumps({'text': chunk.text}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"Gemini streaming failed: {e}, trying OpenAI fallback")
                # Fallback to OpenAI (non-streaming)
                try:
                    from openai import AsyncOpenAI
                    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                    user_prompt = _build_user_prompt(symbol, display_data, display_ma5, display_ma20)
                    response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=500,
                    )
                    full_text = response.choices[0].message.content or ""
                    yield f"event: token\ndata: {json.dumps({'text': full_text}, ensure_ascii=False)}\n\n"
                except Exception as e2:
                    logger.error(f"OpenAI fallback also failed: {e2}")
                    yield f"event: error\ndata: {json.dumps({'message': 'AI analysis unavailable'})}\n\n"
                    return

            # Cache successful result
            if full_text:
                ttl = get_ttl_seconds()
                _ai_cache[symbol] = (full_text, time.time() + ttl)
                yield f"event: done\ndata: {json.dumps({'text': full_text}, ensure_ascii=False)}\n\n"
            else:
                yield f"event: error\ndata: {json.dumps({'message': 'AI returned empty response'})}\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE cancelled for {symbol}")
        except Exception as e:
            logger.error(f"SSE unexpected error for {symbol}: {e}")
            yield f"event: error\ndata: {json.dumps({'message': 'Internal error'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
