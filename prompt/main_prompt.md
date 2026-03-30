# 台股技術分析 Web 系統 — 完整開發對話記錄

## 專案概述

使用 gstack + superpowers 工作流程，從零開始規劃並實作一個台股技術分析 Web 系統。全程由 AI 協助完成架構設計、模組規劃、程式碼實作、架構審查、E2E 驗證、UI 改版、問題排查。

---

## Phase 1：Brainstorming（需求釐清）

### 原始需求

```
建立一個 Web 系統，輸入「台股股票代號」後，完成：
- 取得該股票「最近 30 個交易日」資料
- 計算 MA5（5 日均線）、MA20（20 日均線）
- 前端顯示股價走勢圖、MA5/MA20 曲線
- AI 分析（繁體中文），必須根據實際數據描述趨勢，不可提供投資建議
```

### 逐步釐清的決策（6 輪問答）

| # | 問題 | 決定 | 理由 |
|---|------|------|------|
| 1 | 技術棧 | Next.js + Python FastAPI | Python 金融數據生態成熟，前後端分離好維護 |
| 2 | 資料來源 | yfinance（主）+ TWSE 證交所（fallback） | yfinance 快速開發，TWSE 免費官方免註冊 |
| 3 | AI 分析 | OpenAI → 後改為 Gemini（主）+ OpenAI（fallback） | Gemini 免費額度，OpenAI 作備援 |
| 4 | 圖表庫 | TradingView Lightweight Charts | 專為金融圖表設計，40KB 輕量 |
| 5 | 部署 | 全 Docker 化 | AI 做設定檔幾分鐘搞定，一鍵啟動 |
| 6 | 擴展方向 | 分層做好即可，不過度設計 | 架構乾淨，日後加功能只需疊上去 |

### 關鍵架構討論

**介面抽象分層（用戶主動提出）：**
- UI 層與 DataSource 層用介面隔離
- 資料源可替換（yfinance → TWSE → 未來 DTNO）
- AI 提供者可替換（Gemini → OpenAI → 未來 Ollama）

**高併發 / 高可用討論：**
- 記憶體快取 + fetch dedup（同一支股票並發只打一次 API）
- PostgreSQL 持久化（外部 API 全掛仍能回傳舊資料）
- FallbackDataSource 裝飾器自動切換
- Graceful degradation（AI 掛了仍回圖表）

**快取 TTL 設計（用戶要求精確到交易日）：**
- 不是固定時間，而是綁台股交易日曆
- 盤中 → cache 到 13:30 收盤
- 盤後 → cache 到下一個交易日 09:00
- 假日 → cache 到下一個交易日 09:00
- 需要台股休市日曆模組（holidays JSON）

**MA 往前抓資料（用戶提出）：**
- 要讓 MA20 在第 1 天就有值，需往前多抓 19 天
- 實際抓 49 個交易日（30 顯示 + 19 lookback）
- 只回傳後 30 天的數據和 MA 值給前端

### 內部專案搜尋

開了 3 個 subagent 平行搜尋公司內部專案：

| 專案 | 借鏡 |
|------|------|
| `llm-stock-team-analyzer` | DataSource 抽象、yfinance 封裝、技術指標計算 |
| `iOS_LinEnRuStockApp` | DtNoCacheManager TTL 快取 + fetch dedup |
| `Android_Modules/publicfeature` | CoroutineBaseRepository template method、Expirable LRU Cache |
| `iOS ChipK / cmproductionpage` | DTNO K 線 API 格式、附加資訊 WebSocket |
| `backend/MultiAgentPlatform/agenttoolsmcp` | AgentToolsClient retry 機制 |

**DTNO vs 附加資訊（用戶要求釐清）：**
- DTNO：歷史資料（日 K `3920597`、收盤價 `67784004`），適合我們的需求
- 附加資訊：即時 + 回補（WebSocket），不在這次範圍
- DTNO 需要 JWT token，先不用，留連結做未來參考
- DTNO 資料源申請文件：[Google Doc](https://docs.google.com/document/d/13yS1jZ6Bu6b134MyAX3ClKOsw01xXKhFDJNpid8rZUU/edit?tab=t.0#heading=h.tkmvzuafrrdq)

---

## Phase 2：Design（設計提案）

### 三種架構方案

1. **經典三層（選定）** — 最直覺、分層清晰
2. **BFF 模式** — 多一層轉接，需求簡單不需要
3. **Monolith** — 前後端耦合，失去 Next.js 優勢

### 最終架構

```
┌─────────────────────────────────────────┐
│  Next.js (React + TradingView LWC)      │  UI Layer
│  ├─ Sticky header + search bar          │
│  ├─ Candlestick chart + MA5/MA20        │
│  ├─ AI trend analysis (SSE streaming)   │
│  └─ Collapsible data table + MA columns │
└──────────────────┬──────────────────────┘
                   │ REST API + SSE
┌──────────────────▼──────────────────────┐
│  FastAPI (async)                        │  Service Layer
│  ├─ GET /api/stock/{symbol}             │  ← 資料（快）
│  ├─ GET /api/stock/{symbol}/ai          │  ← AI SSE 串流
│  ├─ CachedDataSource → DB → Fallback   │
│  ├─ IndicatorService (MA5/MA20)         │
│  └─ FallbackAIAnalyzer (Gemini→OpenAI) │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  PostgreSQL (persistent storage)        │
└─────────────────────────────────────────┘
```

---

## Phase 3：Architecture Review（架構審查）

開了兩個平行 review agents（code-architect + code-reviewer），共找到 15 個問題，全部修正：

### Critical（5 項）

1. **DB 沒有 freshness check** — 加入 `_read_fresh_from_db` / `_read_stale_from_db` 分離
2. **前端 null MA 值會炸圖表** — 加 `.filter()` + TypeScript 型別修正
3. **TWSE mock 自我驗證** — 用真實 API column 格式重寫 mock
4. **Cache 無過期測試** — 加 `test_cache_expires_after_ttl`
5. **`asyncio.get_event_loop()` 已棄用** — 改用 `asyncio.get_running_loop()`

### Important（6 項）

6. Symbol 輸入驗證（3-6 位數字）
7. CORS 改為環境變數驅動
8. Frontend Dockerfile 改為 multi-stage production build
9. NEXT_PUBLIC_API_URL 改為 build arg
10. Holiday JSON 缺年份加 warning
11. Stock name 欄位實作

### Low（4 項）

12. `days` 改名 `count`
13. Cache lock 改用 `setdefault`
14. AI 獨立快取
15. 盤前時段 TTL 測試

---

## Phase 4：Implementation（模組化實作）

### 實作策略

使用 **Subagent-Driven Development**，按模組順序執行：

```
Module 1: Infrastructure (Task 1.1-1.3)     → 3 tasks
Module 2: Data Layer (Task 2.1-2.7)          → 7 tasks
Module 3: Business Logic (Task 3.1-3.4)      → 4 tasks
Module 4: Frontend (Task 4.1-4.4)            → 4 tasks
Module 5: Integration (Task 5.1-5.2)         → 2 tasks
```

### 執行順序調整

Task 2.7 (CachedDataSource) 依賴 Module 3 的 `cache_ttl.py`：
- 先跳去做 Task 3.1 + 3.2（交易日曆 + TTL）
- 再回來做 Task 2.7

### 測試結果

- **Backend**: 73 unit tests 全部通過
- **Frontend**: build 通過
- **E2E**: 12 項驗證全部通過

---

## Phase 5：E2E 驗證 + 上線

### E2E 測試結果

| # | 測試 | 結果 |
|---|------|------|
| 1 | Health Check | PASS |
| 2 | Invalid Symbol (AAPL) | PASS — 400 |
| 3 | Symbol Too Short (12) | PASS — 400 |
| 4 | Fetch 2330 台積電 | PASS — 30 筆, MA 全非 null |
| 5 | DB Persistence | PASS — 49 rows in PostgreSQL |
| 6 | Cache Hit | PASS — 0.003s（vs 冷啟動 2.1s）|
| 7 | Another Stock (2317 鴻海) | PASS |
| 8 | Frontend HTTP 200 | PASS |
| 9 | Fallback yfinance → TWSE | PASS |
| 10 | AI 分析 (Gemini 2.5 Flash) | PASS |
| 11 | Unit Tests | PASS — 73/73 |

---

## Phase 6：UI 改版

- **佈局**：`max-w-4xl` → 全螢幕寬度 RWD
- **Header**：固定頂部，搜尋列響應式排列
- **圖表**：桌面 500px / 手機 300px，加圖例
- **明細表**：可收合，加 MA5/MA20 欄位（藍/橘），漲跌紅綠配色
- **主題**：強制淺色（移除 dark mode）

---

## Phase 7：問題排查與修正

### asyncpg date 型別
- 修正：`date_type.fromisoformat(d.date)`

### AI API Key 問題
- OpenAI 額度用完 → 加入 Gemini 作為 primary
- Gemini key 過期 → 換 key（需 `docker-compose down/up` 重載 .env）
- `gemini-2.0-flash` 額度為 0 → 改用 `gemini-2.5-flash`
- Gemini thinking mode 吃 token → `thinking_budget=0`

### AI Cache 問題
- 失敗結果被 cache → 改為只 cache 成功結果

### yfinance 無法抓台股
- 根因：cookie/crumb 認證失敗（非台股專屬，是 yfinance 全域問題）
- 深度調查：`fc.yahoo.com` 被 DNS/ad-blocker 擋、版本過舊
- 修正：升級到 yfinance 1.2.0（curl_cffi 模擬 Chrome）
- 結果：台股資料 + stock name 全部正常

---

## Phase 8：SSE Streaming

### 架構變更

```
Before: GET /api/stock/{symbol}  → 等 AI 完成才回傳（~3.4s）
After:  GET /api/stock/{symbol}      → 立即回傳資料（~0.7s）
        GET /api/stock/{symbol}/ai   → SSE 逐字串流 AI 分析
```

### SSE Event Types

| Event | 說明 |
|-------|------|
| `token` | 部分文字（streaming 中）|
| `done` | 完成（完整文字）|
| `cached` | 快取命中（一次送完）|
| `error` | 錯誤訊息 |

### 安全機制

| 機制 | 說明 |
|------|------|
| Client disconnect | `request.is_disconnected()` 每個 chunk 檢查 |
| Timeout | 30 秒超時自動斷開 |
| AbortController | 前端新搜尋時 abort 前一個 SSE |
| Fallback | Gemini 串流失敗 → OpenAI 非串流 fallback |
| Cache | 成功結果快取，快取命中時不 stream |

### 前端體驗

1. 輸入股票代號 → **圖表 0.7s 內出現**
2. AI 分析區塊開始**逐字打字**（帶閃爍游標動畫）
3. 完成後游標消失，顯示免責聲明

---

## 最終產出

### 文件

| 文件 | 路徑 |
|------|------|
| 設計規格書 | `docs/superpowers/specs/2026-03-30-tw-stock-analyzer-design.md` |
| 實作計畫 | `docs/superpowers/plans/2026-03-30-tw-stock-analyzer.md` |
| 對話記錄 | `prompt/main_prompt.md` |

### Git History（37 commits）

```
1e03350 feat: SSE streaming for AI analysis
52d83c4 fix: upgrade yfinance to 1.2.0 with curl_cffi support
636cf8b feat: ensure project runs anywhere with Docker
dedf176 docs: update spec to match final implementation
8c3fc22 fix: disable Gemini thinking mode, only cache successful AI results
d1a9eb0 fix: use gemini-2.5-flash model, fix dependency versions
b894a1f feat: add Gemini AI analyzer with fallback to OpenAI
14492c4 fix: add error logging to AI analyzer for debugging
ee40d39 feat: add MA5/MA20 columns to trading data table
ee27f86 fix: force light theme, remove dark mode override
99e3290 feat: full-screen RWD layout with improved UI
d6390da fix: convert date string to date object for asyncpg
44121b1 feat: stock API router with validation, AI cache, and name lookup
427e3d5 feat: AI analysis component and main page assembly
3b0b3d6 feat: stock chart with candlestick + MA5/MA20 overlay
45c0dcb feat: stock symbol input component
23f8627 feat: frontend types and API service
36ab27b feat: OpenAI analyzer with graceful degradation
5e5e68e feat: MA calculation service with sliding window
2ecc25f feat: cached data source with smart TTL and expiry test
8d7f9f0 feat: smart cache TTL based on market hours
d78c4a7 feat: Taiwan stock trading calendar with holiday support
3c94fa4 feat: database data source with freshness check and stale fallback
9f8f389 feat: fallback data source decorator with auto-failover
7bd8d70 feat: TWSE fallback data source with ROC date conversion
ee02397 feat: yfinance data source for Taiwan stocks with name lookup
5f0d918 feat: asyncpg connection pool and DB schema migration
2e05b65 feat: DataSource interface and StockDailyData model
fafb99d feat: frontend skeleton with Next.js and Dockerfile
b29da23 feat: backend skeleton with FastAPI and config
5fdccc7 feat: root config files and Docker Compose
cbcd18a docs: design spec and implementation plan
```

### 技術棧

```
Frontend:  Next.js 16 + React + TradingView Lightweight Charts + Tailwind CSS
Backend:   Python FastAPI + asyncpg + yfinance 1.2.0 (curl_cffi)
AI:        Gemini 2.5 Flash SSE streaming (primary) + OpenAI GPT-4o-mini (fallback)
Database:  PostgreSQL 16
Infra:     Docker Compose (3 containers, multi-stage frontend build)
```

### 啟動方式

```bash
git clone <repo-url>
cd scratchProject
./start.sh
# 打開 http://localhost:3000
```

### 效能指標

| 場景 | 耗時 |
|------|------|
| 冷啟動（資料） | ~0.7s |
| 冷啟動（AI streaming 開始） | +0s（與資料請求分離） |
| 冷啟動（AI 完成） | ~2.3s |
| 快取命中 | ~0.003s |
| MA 計算 | ~0.0001s |
| DB 讀寫 | ~0.002s |

---

## 工具與流程

| 階段 | 工具 |
|------|------|
| Brainstorming | superpowers:brainstorming skill |
| 內部專案搜尋 | Explore agents（平行搜尋 3 個目錄） |
| 數據源調研 | WebSearch（yfinance/TWSE/FinMind rate limits） |
| 設計文件 | superpowers:writing-plans skill |
| 架構審查 | feature-dev:code-architect + feature-dev:code-reviewer（平行） |
| 實作執行 | superpowers:subagent-driven-development（20 tasks, 順序執行） |
| yfinance 調查 | general-purpose agent 深度搜尋 GitHub issues |
| E2E 驗證 | Docker Compose + curl + pytest |
| 效能分析 | 手動 benchmark（per-component timing） |

---

## 未來可擴展

| 方向 | 需要做的 |
|------|---------|
| DTNO 資料源 | 取得 JWT token 後加 `DtnoSource` 實作 |
| 更多技術指標 | 在 `IndicatorService` 加 RSI/MACD/布林通道 |
| 即時報價 | 接附加資訊 WebSocket |
| Ollama 本地 AI | 加 `OllamaAnalyzer` 作為第三層 fallback |
| 多股比較 | 前端加 tab/split view |
| Rate limiting | 加 `slowapi` 防止 API 被濫打 |
| 可觀測性 | Prometheus metrics + 結構化 logging |
| CI/CD | GitHub Actions 自動測試 + 部署 |

## 用戶提出的架構重構方向（尚未實作）

```
Headless 設計，架構拆分成：
- 前端
- 後端 API
- 資料儲存體
- 資料來源

功能模組：
- 股票搜尋與資料取回
- MA 計算
- 資料容錯 / 可用性
- 服務的容錯跟 failover
- 可觀測性 / 服務的觀測指標
```
