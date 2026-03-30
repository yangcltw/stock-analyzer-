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
