import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.datasources.models import StockDailyData
from app.services.ai_analyzer import OpenAIAnalyzer


def _make_data() -> list[StockDailyData]:
    return [
        StockDailyData(date=f"2026-03-{i+1:02d}", open=100.0+i, high=105.0+i, low=95.0+i, close=102.0+i, volume=1000)
        for i in range(5)
    ]


@pytest.mark.asyncio
async def test_returns_analysis():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="台積電近期走勢穩定"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("app.services.ai_analyzer.AsyncOpenAI", return_value=mock_client):
        analyzer = OpenAIAnalyzer()
        result = await analyzer.analyze("2330", _make_data(), [102.0]*5, [101.0]*5)

    assert result is not None
    assert len(result) > 0


@pytest.mark.asyncio
async def test_returns_none_on_failure():
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

    with patch("app.services.ai_analyzer.AsyncOpenAI", return_value=mock_client):
        analyzer = OpenAIAnalyzer()
        result = await analyzer.analyze("2330", _make_data(), [102.0]*5, [101.0]*5)

    assert result is None


# --- 邊界測試 ---

@pytest.mark.asyncio
async def test_b9_3_openai_returns_empty_string():
    """OpenAI 回傳空字串時，驗證行為"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=""))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("app.services.ai_analyzer.AsyncOpenAI", return_value=mock_client):
        analyzer = OpenAIAnalyzer()
        result = await analyzer.analyze("2330", _make_data(), [102.0]*5, [101.0]*5)

    # 空字串仍然是有效回傳，不應為 None
    assert result is not None
    assert result == ""


@pytest.mark.asyncio
async def test_b9_5_prompt_contains_no_investment_advice_constraint():
    """驗證 prompt 中包含「不可以提供任何投資建議」的約束"""
    mock_client = MagicMock()
    captured_messages = []

    async def capture_create(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content="分析結果"))]
        return resp

    mock_client.chat.completions.create = capture_create

    with patch("app.services.ai_analyzer.AsyncOpenAI", return_value=mock_client):
        analyzer = OpenAIAnalyzer()
        await analyzer.analyze("2330", _make_data(), [102.0]*5, [101.0]*5)

    system_msg = next(m for m in captured_messages if m["role"] == "system")
    assert "不可以提供任何投資建議" in system_msg["content"]
