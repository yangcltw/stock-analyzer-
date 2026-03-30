# AI 工具分析報告

> 日期：2026-03-30
> 範圍：Taiwan Stock Technical Analyzer — AI Analyzer 模組

---

## 1. 現有架構

```
AIAnalyzer (ABC)
├── GeminiAnalyzer      — Google Gemini 2.5 Flash（primary）
├── OpenAIAnalyzer      — OpenAI GPT-4o-mini（secondary）
└── FallbackAIAnalyzer  — 裝飾器：primary 失敗自動切換 secondary
```

### 組合方式（`routers/stock.py`）

```python
gemini = GeminiAnalyzer()
openai = OpenAIAnalyzer()
analyzer = FallbackAIAnalyzer(gemini, openai)
```

Gemini 為主、OpenAI 為備援。任一失敗回傳 `None`，router 層再 try/except 確保 graceful degradation。

---

## 2. 各 Analyzer 比較

| 項目 | GeminiAnalyzer | OpenAIAnalyzer |
|------|---------------|----------------|
| 模型 | `gemini-2.5-flash` | `gpt-4o-mini` |
| 呼叫方式 | 同步 `generate_content` | 非同步 `chat.completions.create` |
| API Key | `GEMINI_API_KEY` | `OPENAI_API_KEY` |
| SDK | `google-genai==1.14.0` | `openai>=1.60.0` |
| Temperature | 0.3 | 0.3 |
| Max Tokens | 1000 | 500 |
| 思考模式 | `thinking_budget=0`（關閉） | N/A |
| 錯誤處理 | try/except → `None` + log | try/except → `None` + log |

### 共用元件

- **`SYSTEM_PROMPT`**：共用系統提示，約束繁體中文、趨勢描述、禁止投資建議、200 字限制
- **`_build_user_prompt()`**：共用 user prompt 建構函數，包含 OHLCV 資料 + MA 趨勢

---

## 3. 資料流

```
GET /api/stock/{symbol}
    │
    ├─ 取得 30 天 OHLCV + MA5/MA20
    │
    ├─ 檢查 AI cache（symbol → (result, expires_at)）
    │   ├─ cache hit → 直接使用
    │   └─ cache miss ↓
    │
    ├─ FallbackAIAnalyzer.analyze()
    │   ├─ GeminiAnalyzer.analyze()
    │   │   ├─ 成功 → 回傳結果
    │   │   └─ 失敗 → fallback ↓
    │   └─ OpenAIAnalyzer.analyze()
    │       ├─ 成功 → 回傳結果
    │       └─ 失敗 → None
    │
    ├─ 成功時寫入 AI cache（TTL = Smart TTL）
    │
    └─ 回傳 JSON（ai_analysis 可為 null）
```

### 快取策略

- AI 分析結果獨立快取於 `_ai_cache`（與資料快取分開）
- TTL 與資料快取相同（Smart TTL：交易時間到 13:30、收盤後到次交易日 09:00）
- **只快取成功結果**（`ai_result is not None` 才寫入 cache）
- 失敗時不快取，下次請求會重試

---

## 4. 優勢

1. **Interface-driven**：新增 AI provider 只需實作 `AIAnalyzer` ABC
2. **Fallback pattern**：Gemini 掛了自動切 OpenAI，不需手動介入
3. **三層防護**：Analyzer 內部 try/except → FallbackAIAnalyzer 切換 → Router try/except
4. **共用 prompt**：SYSTEM_PROMPT 和 _build_user_prompt 集中管理，避免不一致
5. **Graceful degradation**：AI 全掛不影響股票資料回傳

---

## 5. 已知問題與改善建議

### 5.1 同步 vs 非同步不一致

| 問題 | `GeminiAnalyzer` 使用同步 `generate_content`，會阻塞 event loop |
|------|------|
| 影響 | FastAPI 的 async handler 中呼叫同步 I/O，高並發時效能下降 |
| 建議 | 改用 `await client.aio.models.generate_content()` 或包裹 `run_in_executor` |

### 5.2 缺少 timeout 控制

| 問題 | 兩個 Analyzer 都沒有設定請求 timeout |
|------|------|
| 影響 | API 慢回應時使用者等待過久 |
| 建議 | OpenAI: `timeout=30`；Gemini: `config` 中設定 `http_options` timeout |

### 5.3 缺少 retry 機制

| 問題 | 一次失敗就放棄，切換到 fallback |
|------|------|
| 影響 | 暫時性錯誤（rate limit 429、network glitch）直接降級 |
| 建議 | 加入 1 次 retry with exponential backoff（總 timeout 不超過 10s） |

### 5.4 Fallback 不支援鏈式

| 問題 | `FallbackAIAnalyzer` 只支援 primary + secondary 兩層 |
|------|------|
| 影響 | 如果要加第三個 provider（如 Claude），需要巢狀包裝 |
| 建議 | 改為接受 `list[AIAnalyzer]`，依序嘗試 |

### 5.5 Max Tokens 不一致

| 問題 | Gemini 1000 tokens vs OpenAI 500 tokens |
|------|------|
| 影響 | 不同 provider 回傳長度差異大，UX 不一致 |
| 建議 | 統一為 500 或 800，或抽為 config |

### 5.6 AI Cache 不快取失敗

| 現狀 | 失敗時不寫入 cache，下次請求重試 |
|------|------|
| 優點 | 暫時性錯誤可自動恢復 |
| 風險 | 持續性錯誤（key 無效）會每次請求都打 API |
| 建議 | 失敗時寫入短 TTL cache（如 60s）避免重複打失敗 API |

---

## 6. 可擴展方向

### 6.1 新增 Claude Analyzer

```python
class ClaudeAnalyzer(AIAnalyzer):
    def __init__(self):
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=settings.claude_api_key)

    async def analyze(self, symbol, data, ma5, ma20) -> str | None:
        try:
            user_prompt = _build_user_prompt(symbol, data, ma5, ma20)
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return None
```

### 6.2 改為鏈式 Fallback

```python
class ChainedAIAnalyzer(AIAnalyzer):
    def __init__(self, analyzers: list[AIAnalyzer]):
        self._analyzers = analyzers

    async def analyze(self, symbol, data, ma5, ma20) -> str | None:
        for analyzer in self._analyzers:
            result = await analyzer.analyze(symbol, data, ma5, ma20)
            if result is not None:
                return result
        return None
```

使用方式：
```python
analyzer = ChainedAIAnalyzer([
    GeminiAnalyzer(),
    ClaudeAnalyzer(),
    OpenAIAnalyzer(),
])
```

### 6.3 Config 驅動的 Provider 選擇

```
# .env
AI_PROVIDERS=gemini,claude,openai
AI_TIMEOUT=30
AI_MAX_TOKENS=500
```

根據環境變數動態組合 analyzer chain，不需改程式碼。

---

## 7. 測試覆蓋現況

| 測試 | 覆蓋 |
|------|------|
| `test_ai_analyzer.py::test_returns_analysis` | OpenAI 成功回傳 |
| `test_ai_analyzer.py::test_returns_none_on_failure` | OpenAI 失敗回傳 None |
| `test_ai_analyzer.py::test_b9_3_openai_returns_empty_string` | 空字串處理 |
| `test_ai_analyzer.py::test_b9_5_prompt_contains_no_investment_advice_constraint` | Prompt 約束驗證 |
| `test_stock_router.py::test_b9_1_graceful_degradation_ai_exception` | Router 層 graceful degradation |
| `test_stock_router.py::test_stock_graceful_without_ai` | AI 回傳 None 時 200 |

### 缺少的測試

- GeminiAnalyzer 單元測試
- FallbackAIAnalyzer 單元測試（primary 成功、primary 失敗切 secondary、兩者都失敗）
- AI cache 失敗不快取的行為
- 同步 Gemini 呼叫的效能影響

---

## 8. 依賴一覽

| Package | Version | 用途 |
|---------|---------|------|
| `openai` | >=1.60.0 | OpenAI GPT API |
| `google-genai` | 1.14.0 | Google Gemini API |
| `pydantic-settings` | 2.5.0 | 環境變數管理 |

### 環境變數

| Key | 必要性 | 說明 |
|-----|--------|------|
| `OPENAI_API_KEY` | 選填 | OpenAI fallback |
| `GEMINI_API_KEY` | 選填 | Gemini primary |
| 兩者皆空 | 可運行 | AI 分析為 null，資料正常回傳 |
