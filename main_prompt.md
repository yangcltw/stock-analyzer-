# 台股技術分析 Web 系統 — 完整開發對話記錄

## 專案概述

使用 gstack + superpowers 工作流程，從零開始規劃並實作一個台股技術分析 Web 系統。

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

### 逐步釐清的決策

| 問題 | 決定 | 理由 |
|------|------|------|
| 技術棧 | Next.js + Python FastAPI | Python 金融數據生態成熟，前後端分離好維護 |
| 資料來源 | yfinance（主）+ TWSE 證交所（fallback） | yfinance 快速開發，TWSE 免費官方免註冊 |
| AI 分析 | Gemini 2.5 Flash（主）+ OpenAI（fallback） | 原選 OpenAI，後因額度問題加入 Gemini |
| 圖表庫 | TradingView Lightweight Charts | 專為金融圖表設計，40KB 輕量 |
| 部署 | 全 Docker 化 | AI 做設定檔幾分鐘搞定，一鍵啟動 |
| 資料庫 | PostgreSQL | 高可用需要持久化，未來多實例共享 |
| 擴展方向 | 分層做好即可，不過度設計 | 架構乾淨，日後加功能只需疊上去 |

### 關鍵架構討論

**介面抽象分層（用戶主動提出）：**
- UI 層與 DataSource 層用介面隔離
- 資料源可替換（yfinance → TWSE → 未來 DTNO）
- AI 提供者可替換（Gemini → OpenAI → 未來 Ollama）

**高併發 / 高可用：**
- 記憶體快取 + fetch dedup（同一支股票並發只打一次 API）
- PostgreSQL 持久化（外部 API 全掛仍能回傳舊資料）
- FallbackDataSource 裝飾器自動切換
- Graceful degradation（AI 掛了仍回圖表）

**快取 TTL：**
- 不是固定時間，而是綁台股交易日曆
- 盤中 → cache 到 13:30 收盤
- 盤後 → cache 到下一個交易日 09:00
- 假日 → cache 到下一個交易日 09:00
- 需要台股休市日曆模組（holidays JSON）

**MA 往前抓資料：**
- 要讓 MA20 在第 1 天就有值，需往前多抓 19 天
- 實際抓 49 個交易日（30 顯示 + 19 lookback）
- 只回傳後 30 天的數據和 MA 值給前端

### 內部專案參考

搜尋了公司內部 3 個目錄的相關實作：

| 專案 | 借鏡 |
|------|------|
| `llm-stock-team-analyzer` | DataSource 抽象、yfinance 封裝、技術指標計算 |
| `iOS_LinEnRuStockApp` | DtNoCacheManager TTL 快取 + fetch dedup |
| `Android_Modules/publicfeature` | CoroutineBaseRepository template method、Expirable LRU Cache |
| `iOS ChipK / cmproductionpage` | DTNO K 線 API 格式、附加資訊 WebSocket |
| `backend/MultiAgentPlatform/agenttoolsmcp` | AgentToolsClient retry 機制 |

**DTNO vs 附加資訊：**
- DTNO：歷史資料（日 K `3920597`、收盤價 `67784004`），適合我們的需求
- 附加資訊：即時 + 回補（WebSocket），不在這次範圍
- DTNO 需要 JWT token，這次先不用，留連結做未來參考

---

## Phase 2：Design（設計提案）

### 三種架構方案

1. **經典三層（選定）** — 最直覺、分層清晰
2. **BFF 模式** — 多一層轉接，需求簡單不需要
3. **Monolith** — 前後端耦合，失去 Next.js 優勢

### 設計文件

產出：`docs/superpowers/specs/2026-03-30-tw-stock-analyzer-design.md`

經過 spec self-review 修正了一處：盤中查詢的 TTL 說明需要補充「資料截至前一交易日收盤」。

---

## Phase 3：Architecture Review（架構審查）

開了兩個平行 review agents：

### Architecture Reviewer 發現

| 嚴重度 | 問題 |
|--------|------|
| **High** | DatabaseDataSource 沒有 freshness check，DB 一旦有資料就永不更新 |
| **Medium** | Symbol 無輸入驗證 |
| **Medium** | CORS hardcode localhost:3000 |
| **Medium** | CachedDataSource lock 是 process-local |
| **Low** | `days` 語義模糊，建議改名 `count` |
| **Low** | Spec 有 `name` 欄位但沒實作 |
| **Low** | Holiday JSON 缺年份無警告 |

### Implementation Reviewer 發現

| 嚴重度 | 問題 |
|--------|------|
| **Critical** | TWSE mock 自我驗證，沒對照真實 API 格式 |
| **Critical** | 前端 null MA 值會炸 lightweight-charts |
| **Critical** | Cache 無過期測試 |
| **Important** | `asyncio.get_event_loop()` 已棄用 |
| **Important** | Frontend Dockerfile 用 npm run dev |
| **Important** | NEXT_PUBLIC_API_URL 是 build-time 變數 |

### 全部 15 項修正

所有問題都在實作計畫中修正，重新產出完整計畫。

---

## Phase 4：Implementation（模組化平行實作）

### 實作計畫拆分

按模組拆分為 5 個 Module、20 個 Tasks：

```
Module 1: Infrastructure (Task 1.1-1.3)
    ↓ 完成後展開
Module 2: Data Layer (Task 2.1-2.7)    ← 順序執行
Module 3: Business Logic (Task 3.1-3.4) ← 順序執行
Module 4: Frontend (Task 4.1-4.4)       ← 順序執行
    ↓ 全部完成後
Module 5: Integration (Task 5.1-5.2)
```

選擇 **順序執行（B）**，零衝突風險。

### 執行方式

使用 **Subagent-Driven Development**：
- 每個 Task 開一個 subagent 實作
- 簡單 Task 用 haiku/sonnet，複雜 Task 用 opus（後改為全部 opus）
- TDD：先寫測試 → 驗證失敗 → 實作 → 驗證通過 → commit

### 執行順序調整

Task 2.7 (CachedDataSource) 依賴 Module 3 的 `cache_ttl.py`，所以：
- 先跳去做 Task 3.1 + 3.2（交易日曆 + TTL）
- 再回來做 Task 2.7

### 實作過程中的修正

| 問題 | 修正 |
|------|------|
| asyncpg 寫入 date 欄位需要 `datetime.date` 物件 | `date_type.fromisoformat(d.date)` |
| DB 寫入失敗不應阻擋回傳 | `_write_to_db` 包 try/except |
| yfinance 在 Docker 內 SSL 問題 | Fallback 機制自動切到 TWSE |
| OpenAI API 額度用完 | 加入 Gemini 作為主要 AI |
| Gemini API key 過期 | 換 key + `docker-compose down/up` 重載 .env |
| Gemini 2.0-flash 額度為 0 | 改用 gemini-2.5-flash |
| Gemini 2.5 回應被截斷 | 關閉 thinking mode（`thinking_budget=0`） |
| httpx 版本衝突（google-genai vs openai） | 放寬 httpx 版本約束 |
| openai SDK 與新 httpx 不相容 | 升級 openai 到 >=1.60.0 |
| AI 失敗結果被 cache | 只 cache 成功結果（`if ai_result is not None`） |

---

## Phase 5：E2E 驗證

### Docker Compose 啟動

3 個 container 全部啟動：
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

### E2E 測試結果

| # | 測試 | 結果 |
|---|------|------|
| 1 | Health Check | PASS — `{"status": "ok"}` |
| 2 | Invalid Symbol (AAPL) | PASS — 400 |
| 3 | Symbol Too Short (12) | PASS — 400 |
| 4 | Fetch 2330 台積電 | PASS — 30 筆, MA 全非 null |
| 5 | DB Persistence | PASS — 49 rows in PostgreSQL |
| 6 | Cache Hit | PASS — 第二次走快取 |
| 7 | Another Stock (2317 鴻海) | PASS — close=199.5 |
| 8 | Frontend HTTP 200 | PASS |
| 9 | Frontend 顯示「台股技術分析」 | PASS |
| 10 | Unit Tests | PASS — 73/73 |
| 11 | Fallback yfinance → TWSE | PASS — 自動切換 |
| 12 | AI 分析 (Gemini 2.5 Flash) | PASS — 303 字完整分析 |

---

## Phase 6：UI 改版

### 改動

| 改動 | 桌面 | 手機 |
|------|------|------|
| 佈局 | 全螢幕寬度 | 同 |
| Header | 固定頂部，標題 + 搜尋並排 | 上下堆疊 |
| 圖表 | 500px 高 | 300px 高 |
| 圖例 | MA5/MA20/漲跌顏色 | 同 |
| 明細表 | 可收合，含 MA5/MA20 欄位，漲跌配色 | 隱藏成交量 |
| 主題 | 強制淺色（移除 dark mode） | 同 |

---

## 最終產出

### 文件

| 文件 | 路徑 |
|------|------|
| 設計規格書 | `docs/superpowers/specs/2026-03-30-tw-stock-analyzer-design.md` |
| 實作計畫 | `docs/superpowers/plans/2026-03-30-tw-stock-analyzer.md` |

### Git History（33 commits）

```
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

### 測試

- **Backend**: 73 unit tests，全部通過
- **Frontend**: build 通過
- **E2E**: 12 項驗證全部通過

### 技術棧

```
Frontend:  Next.js 16 + React + TradingView Lightweight Charts + Tailwind CSS
Backend:   Python FastAPI + asyncpg + yfinance + httpx
AI:        Gemini 2.5 Flash (primary) + OpenAI GPT-4o-mini (fallback)
Database:  PostgreSQL 16
Infra:     Docker Compose (3 containers)
```

### 啟動方式

```bash
cp .env.example .env
# 填入 GEMINI_API_KEY 和/或 OPENAI_API_KEY
docker-compose up --build
# 打開 http://localhost:3000
```

---

## 使用的工具與流程

| 階段 | 工具 |
|------|------|
| Brainstorming | superpowers:brainstorming skill |
| 內部專案搜尋 | Explore agents（平行搜尋 3 個目錄） |
| 數據源調研 | WebSearch（yfinance/TWSE/FinMind rate limits） |
| 設計寫入 | superpowers:writing-plans skill |
| 架構審查 | feature-dev:code-architect + feature-dev:code-reviewer（平行） |
| 實作執行 | superpowers:subagent-driven-development（20 tasks） |
| E2E 驗證 | Docker Compose + curl + pytest |

### 未來可擴展

| 方向 | 需要做的 |
|------|---------|
| DTNO 資料源 | 取得 JWT token 後加 `DtnoSource` 實作 |
| 更多技術指標 | 在 `IndicatorService` 加 RSI/MACD/布林通道 |
| 即時報價 | 接附加資訊 WebSocket |
| Ollama 本地 AI | 加 `OllamaAnalyzer` 作為第三層 fallback |
| 多股比較 | 前端加 tab/split view |
