# Taiwan Stock Analyzer - QA Conversation Log

> 日期：2026-03-30
> 專案：Taiwan Stock Technical Analyzer
> 工具：Claude Code (Opus 4.6)

---

## Q1: 專案概覽

**User:**
這個目錄底下，有一個專案正在實作專案，內容是

**Assistant:**
這個目錄下有一個 **Taiwan Stock Technical Analyzer（台股技術分析系統）** 專案，目前狀態是：

- **已完成**：設計規格書（spec）和實作計畫（plan）
- **尚未開始**：實際的程式碼（backend/frontend 都還沒有任何檔案）

### 專案內容

一個 Web 系統，功能是：
1. 輸入台股代號（如 2330）
2. 取得最近 30 個交易日的 OHLCV 資料
3. 計算 MA5 / MA20 均線
4. 用 TradingView Lightweight Charts 顯示股價走勢圖 + 均線
5. 透過 OpenAI 產生繁體中文 AI 趨勢分析

### 技術架構

| 層 | 技術 |
|---|---|
| 前端 | Next.js + TradingView LWC |
| 後端 | Python FastAPI (async) |
| 資料來源 | yfinance（主）→ TWSE（備援） |
| 資料庫 | PostgreSQL |
| AI 分析 | OpenAI API |
| 部署 | Docker Compose（3 個容器） |

---

## Q2: 建立資料驗證工具

**User:**
做驗證資料的工具，並且資料源不要用 yfinance

**Assistant:**
建立了 `tools/verify_stock_data.py`，使用 TWSE 證交所官方 API 作為獨立資料源。

### 功能

| 模式 | 用法 |
|------|------|
| 基本驗證 | `python3 tools/verify_stock_data.py 2330` |
| JSON 輸出 | `python3 tools/verify_stock_data.py 2330 --json` |
| 比對後端 API | `python3 tools/verify_stock_data.py 2330 --compare http://localhost:8000/api/stock/2330` |
| 自訂天數 | `python3 tools/verify_stock_data.py 2330 --days 20` |

### 資料源
- **TWSE 證交所官方 API**（`exchangeReport/STOCK_DAY`），不用 yfinance
- 自動跨月抓取，確保 MA20 從顯示第一天就有值（抓 49 天算 30 天）

### 驗證項目
- OHLCV 五項價量資料
- MA5 / MA20 獨立計算
- `--compare` 模式：逐日逐欄位比對後端 API，列出所有差異

---

## Q3: 匯出 Excel

**User:**
幫我抓 2330 1301 跟 0050 的資料存成 xls

**Assistant:**
檔案儲存在 `tools/stock_data_2330_1301_0050.xlsx`，內含 3 個分頁：

| 分頁 | 內容 |
|------|------|
| **2330** | 台積電 最近 30 個交易日 |
| **1301** | 台塑 最近 30 個交易日 |
| **0050** | 元大台灣50 最近 30 個交易日 |

每個分頁都包含：
- OHLCV（開高低收量）逐日資料
- MA5 / MA20 均線值
- 摘要區（最高/最低收盤、漲跌幅、最新均線狀態）

資料源全部來自 TWSE 證交所官方 API。

---

## Q4: MA 資料來源釐清

**User:**
所以 MA5 跟 MA20 交易所都會有還是你算的

**Assistant:**
MA5 和 MA20 是**自己算的**。

TWSE API（`STOCK_DAY`）只提供每日的原始 OHLCV 資料，不提供任何均線值。

計算邏輯在 `tools/verify_stock_data.py` 的 `calculate_ma` 函式，就是標準的 SMA（簡單移動平均）：取最近 N 天收盤價加總除以 N。

所以這個驗證工具的可信度取決於：
- **OHLCV 原始資料** → 直接來自 TWSE，可信
- **MA5 / MA20** → 用 TWSE 的收盤價自己算的，算法正確但是**獨立計算結果**，不是交易所提供的官方值

這也是為什麼 `--compare` 模式有意義：用同樣的 TWSE 原始資料獨立算 MA，再跟後端 API 的結果交叉比對，確認兩邊算出來一致。

---

## Q5: 跑後端測試

**User:**
跑測試

**Assistant:**
**73 個測試全部通過**，跑了 1.06 秒。

```
======================== 73 passed, 2 warnings in 1.06s ========================
```

| 模組 | 測試數 | 狀態 |
|------|--------|------|
| ai_analyzer | 4 | PASS |
| cache_ttl | 7 | PASS |
| cached_source | 5 | PASS |
| db_source | 6 | PASS |
| fallback_source | 5 | PASS |
| indicator (MA) | 8 | PASS |
| stock_router (API) | 13 | PASS |
| trading_calendar | 7 | PASS |
| twse_source | 6 | PASS |
| yfinance_source | 9 | PASS |

有 2 個 warning（Pydantic v2 deprecation 和 LibreSSL），不影響功能。

---

## Q6: 用驗證工具比對後端 API

**User:**
用剛剛寫的數據工具跑

**Assistant:**
三檔全部驗證通過：

| 股票 | OHLCV | MA5 | MA20 | 結果 |
|------|-------|-----|------|------|
| **2330** 台積電 | 一致 | 一致 | 一致 | **PASS** |
| **1301** 台塑 | 一致 | 一致 | 一致 | **PASS** |
| **0050** 元大台灣50 | 一致 | 一致 | 一致 | **PASS** |

### 驗證方式
使用 `verify_stock_data.py --compare` 模式，從 TWSE 官方 API 獨立抓取資料，與後端 API（`http://localhost:8000/api/stock/{symbol}`）逐日逐欄位比對。

### 驗證指令
```bash
python3 tools/verify_stock_data.py 2330 --compare http://localhost:8000/api/stock/2330
python3 tools/verify_stock_data.py 1301 --compare http://localhost:8000/api/stock/1301
python3 tools/verify_stock_data.py 0050 --compare http://localhost:8000/api/stock/0050
```

### 結論
後端 API 回傳的資料（OHLCV + MA5 + MA20）與 TWSE 官方資料獨立計算的結果完全一致，零差異。
