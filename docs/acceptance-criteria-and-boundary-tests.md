# 驗收標準與邊界測試清單

> 由 QA Engineer、Backend Engineer、Frontend Engineer 三方討論產出
> 日期：2026-03-30

---

# Part 1: Taiwan Stock Technical Analyzer

## 1. 功能驗收標準

### 1.1 API 層（`GET /api/stock/{symbol}`）

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| A1-1 | 回傳正確 JSON 結構 | 回應包含 `symbol`、`name`、`data`（30 筆）、`ma5`（30 個非 null）、`ma20`（30 個非 null） | 任一欄位缺失、data 不足 30 筆、ma 含 null |
| A1-2 | 日期排序正確 | `data` 陣列按日期升序排列 | 日期亂序 |
| A1-3 | OHLCV 資料完整 | 每筆 data 含 date/open/high/low/close/volume 且 > 0 | 任一欄位為 null 或負值 |
| A1-4 | 無效股票代號處理 | 回傳 4xx + 明確錯誤訊息 | 500 錯誤或無意義回應 |
| A1-5 | `GET /health` 正常 | 回傳 200 + 健康狀態 | 非 200 |
| A1-6 | CORS 設定正確 | 前端 origin 可跨域呼叫 | 跨域被拒 |
| A1-7 | Response 時間 | Cache hit < 100ms；Cache miss < 10s | 超時無回應 |

### 1.2 DataSource 層

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| A2-1 | yfinance 正常取資料 | 回傳 49 個交易日 OHLCV | 回傳不足或例外未處理 |
| A2-2 | yfinance 失敗自動 fallback TWSE | 自動切換，不回傳錯誤 | fallback 未觸發 |
| A2-3 | 全部 API 掛 → stale DB | 回傳 DB 最新歷史資料 + 時間戳 | 直接回傳錯誤 |
| A2-4 | 資料寫入 DB | 成功取得後 DB 有記錄 | 無記錄或 UNIQUE 衝突 |
| A2-5 | symbol 格式轉換 | `2330` → `2330.TW` | 格式錯誤 |

### 1.3 Cache 層

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| A3-1 | 快取命中不呼叫外部 API | TTL 內第二次請求不觸發外部呼叫 | 重複呼叫 |
| A3-2 | Smart TTL 正確 | 交易時間 → 13:30；收盤後 → 次交易日 09:00 | TTL 計算錯誤 |
| A3-3 | 並發 dedup | 同時 10 個相同 symbol 請求只 1 次 API 呼叫 | 多次呼叫 |
| A3-4 | 過期後重新取得 | TTL 到期後重新取得 | 持續回傳過期資料 |

### 1.4 Indicator 計算

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| A4-1 | MA5 正確 | 每個值 = 前 5 日 close 算術平均 | 誤差超過浮點精度 |
| A4-2 | MA20 正確 | 每個值 = 前 20 日 close 算術平均 | 誤差超過浮點精度 |
| A4-3 | 30 個 MA 全部非 null | 49 天資料確保 30 天 MA20 都有值 | 含 null |

### 1.5 AI Analyzer

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| A5-1 | 繁體中文回覆 | `ai_analysis` 為繁體中文 | 英文、簡體或亂碼 |
| A5-2 | 不含投資建議 | 僅描述趨勢，無「建議買入/賣出」 | 包含投資建議 |
| A5-3 | Graceful degradation | OpenAI 失敗時仍回傳 data/ma | 整個 API 500 |

### 1.6 Frontend

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| A6-1 | 圖表顯示 | 輸入代號後呈現 K 線 + MA5(藍)/MA20(橘) | 圖表不顯示或 MA 缺失 |
| A6-2 | Loading 狀態 | 搜尋中顯示 loading indicator | 無提示 |
| A6-3 | 錯誤顯示 | 無效代號或網路錯誤 → 使用者友善訊息 | 白頁或 console 錯誤 |
| A6-4 | AI 分析區塊 | 有 AI → 文字；無 AI → placeholder | 區塊消失或顯示錯誤 |
| A6-5 | Responsive | 不同螢幕寬度自動調整 | 溢出或過小 |
| A6-6 | XSS 防護 | 所有動態文字用 React JSX 渲染（自動 escape） | 可執行腳本 |

---

## 2. 邊界測試案例

### 2.1 資料源切換

| # | 場景 | 預期行為 |
|---|------|---------|
| B1-1 | yfinance timeout（>10s） | fallback TWSE |
| B1-2 | yfinance 回傳空資料 | 視為失敗，fallback TWSE |
| B1-3 | yfinance 回傳 < 49 天 | fallback TWSE |
| B1-4 | yfinance + TWSE 失敗，DB 有資料 | 回傳 stale + 時間戳 |
| B1-5 | 三者全無資料 | 回傳明確錯誤（非 500） |
| B1-6 | yfinance HTTP 429 | 觸發 fallback，不 retry 阻塞 |
| B1-7 | yfinance 回傳 NaN 欄位 | 過濾或替換 NaN，不污染 MA 計算 |
| B1-8 | Primary 回傳空列表（非異常） | FallbackSource 不觸發 fallback — **需確認設計意圖** |

### 2.2 YFinanceSource 特殊場景

| # | 場景 | 預期行為 |
|---|------|---------|
| B2-1 | 上櫃股票（如 6488） | 目前 `.TW` 硬編碼會失敗 — **已知風險，需決定是否支援 `.TWO`** |
| B2-2 | ETF 代號 `0050` | 正常組合 `0050.TW` 取得資料 |
| B2-3 | `run_in_executor` 無 timeout | 網路斷線時可能無限期等待 — **高優先修復** |
| B2-4 | `ticker.info` 拋異常 | `get_stock_name` 未捕捉 — **需加 try/except** |

### 2.3 TWSESource 特殊場景

| # | 場景 | 預期行為 |
|---|------|---------|
| B3-1 | ROC 跨年：114/12/31 → 115/01/02 | 正確轉換 2025-12-31 → 2026-01-02 |
| B3-2 | TWSE stat 非 "OK" | 該月份跳過，3 月都失敗 → ValueError |
| B3-3 | TWSE 回傳欄位不足 | try/except 捕捉 IndexError，跳過該筆 |
| B3-4 | httpx timeout 異常未被捕捉 | `_fetch_month` 的超時異常會穿透 — **高優先修復** |
| B3-5 | 高價股含逗號 "1,234.00" | 已正確處理 `.replace(",", "")` |

### 2.4 Database 邊界

| # | 場景 | 預期行為 |
|---|------|---------|
| B4-1 | DB 有部分資料 < 49 天 | 走 upstream 取完整資料 |
| B4-2 | DB 資料剛好 = 49 天且新鮮 | 直接回傳，不呼叫 upstream |
| B4-3 | 連線池耗盡 | 有 timeout 機制，不永久 hang |
| B4-4 | `_write_to_db` 失敗 | **不應影響資料回傳** — 需 try/except 包裹 |
| B4-5 | 並發 UPSERT 同一 symbol/date | `ON CONFLICT DO UPDATE` 保證正確 |
| B4-6 | DB 連線中斷 | 仍可從外部 API 取資料（略過 DB） |
| B4-7 | Schema 未初始化 | 自動 migration 或明確錯誤 |

### 2.5 快取 TTL 邊界

| # | 場景 | 預期 TTL |
|---|------|---------|
| B5-1 | 週一 09:00 查詢 | → 當天 13:30 |
| B5-2 | 週一 13:29 查詢 | → 13:30（剩 1 分鐘） |
| B5-3 | 週一 13:30 查詢 | → 次交易日 09:00 |
| B5-4 | 週一 13:31 查詢 | → 週二 09:00 |
| B5-5 | 週五 14:00 查詢 | → 下週一 09:00 |
| B5-6 | 國定假日前一天 14:00 | → 假日後首交易日 09:00 |
| B5-7 | 連續假期中查詢 | → 連假後首交易日 09:00 |
| B5-8 | 跨年底查詢 | holidays JSON 跨年正確處理 |
| B5-9 | holidays JSON 缺失 | fallback 僅用週六日規則，或明確錯誤 |
| B5-10 | holidays JSON 格式錯誤 | 錯誤處理，不 crash |

### 2.6 並發 Dedup

| # | 場景 | 預期行為 |
|---|------|---------|
| B6-1 | 同時 100 個相同 symbol | 僅 1 次 API 呼叫，100 個回應一致 |
| B6-2 | 同時不同 symbol（2330 + 2317） | 各自獨立，互不阻塞 |
| B6-3 | Dedup 中一個 cancel/timeout | 其餘請求仍正常回傳 |
| B6-4 | Dedup 中 API 失敗 | 所有等待中請求都收到 fallback 結果 |

### 2.7 MA 計算邊界

| # | 場景 | 預期行為 |
|---|------|---------|
| B7-1 | 剛好 5 筆算 MA5 | 回傳 1 個有效值 |
| B7-2 | 4 筆算 MA5 | 回傳 None |
| B7-3 | 剛好 20 筆算 MA20 | 回傳 1 個有效值 |
| B7-4 | 19 筆算 MA20 | 回傳 None |
| B7-5 | 49 筆完整資料 | MA5 有 45 值、MA20 有 30 值，最後 30 筆全 non-null |
| B7-6 | 全部 close 相同 | MA = close 價格 |
| B7-7 | close 含極大值 999999.99 | 不溢位 |
| B7-8 | 浮點精度 0.1+0.2+0.3+0.4+0.5 | `round()` 控制到小數後 2 位 |
| B7-9 | prices 為空列表 | 回傳空列表 |
| B7-10 | prices 含 None/NaN | 含 None 的窗口回傳 None |

### 2.8 API 輸入邊界

| # | 場景 | 預期行為 |
|---|------|---------|
| B8-1 | 空字串 `""` | 400 Bad Request |
| B8-2 | 不存在代號 `9999` | 404 或明確錯誤 |
| B8-3 | 含腳本標籤字串 | 400，不執行 |
| B8-4 | SQL injection 字串 | 參數化查詢，安全處理 |
| B8-5 | 256+ 字元 | 400 |
| B8-6 | 全空白 `"   "` | 400 |
| B8-7 | `AAPL`（非台股） | 明確錯誤 |
| B8-8 | `0050`（ETF） | 正常處理 |
| B8-9 | 全形數字 `２３３０` | 400 或自動轉換 |
| B8-10 | Path traversal `../../etc/passwd` | 400，建議正則 `^[0-9A-Za-z]{1,10}$` |

### 2.9 AI Analyzer 邊界

| # | 場景 | 預期行為 |
|---|------|---------|
| B9-1 | API key 無效/過期 | Graceful degradation |
| B9-2 | API timeout > 30s | Graceful degradation，不等 AI |
| B9-3 | 回傳空字串 | `ai_analysis` 為 null，非空字串 |
| B9-4 | Token 超限 | Graceful degradation |
| B9-5 | 回傳投資建議內容 | Prompt 約束應防止，前端仍顯示 |
| B9-6 | 並發 10 個 AI 請求 | 考慮 OpenAI RPM/TPM 限制 |

### 2.10 Frontend UI 邊界

| # | 場景 | 預期行為 |
|---|------|---------|
| B10-1 | 空白輸入按搜尋 | 不發 API，顯示提示 |
| B10-2 | 輸入 XSS 字串 | 純文字處理，不執行 |
| B10-3 | 快速連續點擊 5 次 | debounce/防重複，最多 1 次請求 |
| B10-4 | 搜尋中再次點擊 | 按鈕 disabled 或取消前次 |
| B10-5 | 前後空白 ` 2330 ` | 自動 trim |
| B10-6 | API 回傳空 data `[]` | 不 crash，顯示「無資料」 |
| B10-7 | 所有價格相同 | 水平線，不 NaN |
| B10-8 | 極端價格差 1 vs 10000 | Y 軸正確縮放 |
| B10-9 | 視窗 1920px → 320px | 圖表 responsive |
| B10-10 | 重新搜尋 | 舊圖表清除，新資料渲染 |
| B10-11 | 組件卸載 | `chart.remove()` 避免記憶體洩漏 |
| B10-12 | `ai_analysis` 為 null/undefined/空字串 | 顯示 placeholder |
| B10-13 | `ai_analysis` 含 HTML | 純文字渲染，防 XSS |
| B10-14 | `ai_analysis` 超長 5000+ 字 | 正常顯示，可加捲動 |
| B10-15 | Backend > 5s | 持續 loading，建議 15s timeout |
| B10-16 | Backend 回傳非 JSON | catch 錯誤，顯示通用訊息 |
| B10-17 | 缺少必要欄位 | Defensive check，不 undefined error |
| B10-18 | 連續搜 2330 → 2317 → 2454 | AbortController 取消前次，僅顯示最後結果 |
| B10-19 | 網路斷線 | 顯示「網路連線異常」 |
| B10-20 | Mobile 320px 到 Desktop 1920px | 垂直堆疊，元件不超出 |

---

# Part 2: prompt-logger Plugin

## 3. 功能驗收標準

### 3.1 Hooks

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| H1-1 | init-db 建立目錄與 DB | `~/.prompt-logger/` + `exports/` + `logs.db` 含 logs 表 | 缺失 |
| H1-2 | init-db 冪等性 | 重複執行不報錯不覆蓋 | 重複執行出錯 |
| H1-3 | DB 權限 0600 | `-rw-------` | 其他使用者可讀 |
| H1-4 | record-prompt 正確記錄 | session_id/timestamp/project/branch/prompt 皆正確 | 欄位錯誤 |
| H1-5 | record-prompt < 5 秒 | 正常 < 1 秒 | 超過 timeout |
| H1-6 | session-summary 更新 tools_used | session 記錄的 tools_used 被更新 | 仍為 NULL |
| H1-7 | session-summary < 10 秒 | 正常完成 | 超過 timeout |
| H1-8 | WAL mode 啟用 | `PRAGMA journal_mode` = `wal` | 非 WAL |

### 3.2 /log-search

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| S1-1 | 關鍵字搜尋 | 回傳含關鍵字的記錄 | 無結果或不相關 |
| S1-2 | --project 篩選 | 僅指定專案 | 混入其他專案 |
| S1-3 | --from/--to 範圍 | 僅範圍內 | 範圍外出現 |
| S1-4 | --rating 篩選 | 僅指定評分 | 其他評分混入 |
| S1-5 | --limit 限制 | 預設 20，自訂有效 | 超出 limit |
| S1-6 | 表格格式 | 含 ID、時間、專案、prompt 前 60 字、評分 | 欄位缺失 |

### 3.3 /log-rate

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| R1-1 | 無參數 → 未評分記錄 | 最近 5 筆 rating IS NULL | 列出已評分 |
| R1-2 | ID + 分數直接評分 | rating 更新成功 | 更新失敗 |
| R1-3 | --note 備註 | rating_note 正確儲存 | 遺失 |
| R1-4 | --tags 標籤 | tags 為正確 JSON array | 格式錯誤 |
| R1-5 | 評分範圍 1-5 | 1~5 接受，其他拒絕 | 0/6/-1 被接受 |

### 3.4 /log-stats

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| T1-1 | 總互動次數 | COUNT(*) 一致 | 數字錯誤 |
| T1-2 | 日均次數 | 計算合理 | 除以 0 |
| T1-3 | 按專案分佈 | 加總 = 總數 | 不符 |
| T1-4 | 按評分分佈 | 含未評分統計 | 忽略 NULL |
| T1-5 | 工具 Top 5 | JSON 解析正確統計 | 解析失敗 |
| T1-6 | --days 參數 | 僅統計指定天數 | 忽略參數 |

### 3.5 /log-export

| # | 驗收標準 | Pass 條件 | Fail 條件 |
|---|---------|----------|----------|
| E1-1 | CSV 正確 | Excel/Sheets 可開啟 | 解析錯誤 |
| E1-2 | JSON 正確 | `jq .` 可解析 | invalid JSON |
| E1-3 | Markdown 正確 | 可讀表格 | 格式錯亂 |
| E1-4 | --from/--to 篩選 | 範圍正確 | 含範圍外 |
| E1-5 | 匯出至正確目錄 | `~/.prompt-logger/exports/` | 位置錯誤 |
| E1-6 | 檔名含時間戳 | 不覆蓋舊檔 | 覆蓋 |

---

## 4. 邊界測試案例

### 4.1 DB 初始化冪等性

| # | 場景 | 預期行為 |
|---|------|---------|
| B11-1 | 首次 SessionStart（無 DB） | 建立目錄 + DB + 表 + 索引 |
| B11-2 | 第二次 SessionStart（DB 已存在） | 不報錯、不覆蓋 |
| B11-3 | DB 檔案損壞 | 明確錯誤，不靜默忽略 |
| B11-4 | 目錄存在但無 DB | 僅建 DB |
| B11-5 | 磁碟空間不足 | 明確錯誤，不產生空檔 |
| B11-6 | 同時兩個 session 觸發 init | 不 race condition |

### 4.2 Hook Timeout

| # | 場景 | 預期行為 |
|---|------|---------|
| B12-1 | record-prompt 4.9 秒完成 | 正常記錄 |
| B12-2 | record-prompt 超 5 秒 | 被中斷，不影響使用者 |
| B12-3 | session-summary 9.9 秒完成 | 正常更新 |
| B12-4 | session-summary 超 10 秒 | 被中斷，已記錄的 prompt 不受影響 |
| B12-5 | init-db 超 5 秒 | 被中斷，下次重試 |

### 4.3 超長 Prompt

| # | 場景 | 預期行為 |
|---|------|---------|
| B13-1 | 1 字元 | 正確記錄 |
| B13-2 | 10,000 字元 | 正確記錄，不截斷 |
| B13-3 | 100,000 字元 | 正確記錄或有截斷策略 |
| B13-4 | 含換行、tab、特殊空白 | 正確儲存還原 |
| B13-5 | 含 emoji、CJK、組合字元 | UTF-8 正確處理 |
| B13-6 | 空 prompt `""` | 不 crash |

### 4.4 SQL Injection 防護

| # | 場景 | 預期行為 |
|---|------|---------|
| B14-1 | `'; DROP TABLE logs; --` | 正確記錄為文字，表不被刪 |
| B14-2 | 含單引號 `it's a test` | 正確儲存 |
| B14-3 | 含雙引號 `say "hello"` | 正確儲存 |
| B14-4 | 含反斜線 `path\to\file` | 正確儲存 |
| B14-5 | project 名含特殊字元 | 正確儲存 |
| B14-6 | /log-search 含 `%` 或 `_` | LIKE 正確 escape |
| B14-7 | /log-rate --note 含 SQL | 參數化查詢 |

### 4.5 Rating 範圍驗證

| # | 場景 | 預期行為 |
|---|------|---------|
| B15-1 | rating = 1 | 接受 |
| B15-2 | rating = 5 | 接受 |
| B15-3 | rating = 0 | 拒絕 |
| B15-4 | rating = 6 | 拒絕 |
| B15-5 | rating = -1 | 拒絕 |
| B15-6 | rating = null | 不更新 |
| B15-7 | rating = "abc" | 拒絕 |
| B15-8 | rating = 3.5 | 拒絕（僅整數） |
| B15-9 | rating = "" | 拒絕 |
| B15-10 | 對不存在的 ID 評分 | 明確錯誤 |

### 4.6 Export 格式

| # | 場景 | 預期行為 |
|---|------|---------|
| B16-1 | CSV 中 prompt 含逗號 | 雙引號包裹 |
| B16-2 | CSV 中 prompt 含雙引號 | escape 為 `""` |
| B16-3 | CSV 中 prompt 含換行 | 雙引號包裹，多行保留 |
| B16-4 | JSON 中含特殊跳脫字元 | JSON escape 正確 |
| B16-5 | JSON 中 tags（JSON in TEXT） | 巢狀 JSON array |
| B16-6 | Markdown 中 prompt 含 `|` | pipe 正確 escape |
| B16-7 | 匯出 0 筆 | 含 header 的空檔或提示無資料 |
| B16-8 | 匯出 10,000 筆 | < 30 秒完成 |

### 4.7 WAL 並發

| # | 場景 | 預期行為 |
|---|------|---------|
| B17-1 | 寫入中 /log-search | 不被阻塞 |
| B17-2 | 寫入中 /log-export | 不被阻塞，資料一致 |
| B17-3 | 兩個 session 同時寫入 | 不 SQLITE_BUSY 或自動 retry |
| B17-4 | 大量寫入 WAL 大小 | 定期 checkpoint |

### 4.8 空資料庫

| # | 場景 | 預期行為 |
|---|------|---------|
| B18-1 | /log-search 無記錄 | 「無結果」，不報錯 |
| B18-2 | /log-stats 無記錄 | 0 次互動，不除以 0 |
| B18-3 | /log-rate 無未評分 | 「無待評分記錄」 |
| B18-4 | /log-export 無記錄 | 含 header 空檔或提示 |

### 4.9 Session ID

| # | 場景 | 預期行為 |
|---|------|---------|
| B19-1 | 同一 session 多次 prompt | session_id 相同 |
| B19-2 | 不同 session | session_id 不同 |
| B19-3 | session-summary 更新 | 只影響當前 session |
| B19-4 | session_id 含特殊字元 | 正確儲存查詢 |

---

# Part 3: 已知重大風險（Backend Code Review）

以下為 Backend Engineer 審查已實作程式碼後發現的風險：

| 優先級 | 模組 | 風險 | 建議 |
|--------|------|------|------|
| **高** | YFinanceSource | `run_in_executor` 無 timeout，可能無限期掛起 | 外層加 `asyncio.wait_for` |
| **高** | TWSESource | `_fetch_month` 未捕捉 httpx timeout 異常 | 加 try/except 包裹 `client.get` |
| **高** | DatabaseDataSource | `_write_to_db` 失敗會阻止已取得資料回傳 | try/except 包裹，寫入失敗不影響回傳 |
| **高** | YFinanceSource | `.TW` 硬編碼，上櫃股票（`.TWO`）無法查詢 | 決定是否支援上櫃，加 `.TWO` 判斷 |
| **中** | YFinanceSource | DataFrame 可能含 NaN | 過濾或替換 NaN |
| **中** | FallbackDataSource | Primary 錯誤訊息被吞掉 | 記錄 primary exception log |
| **中** | Router（待實作） | 缺少 symbol 格式驗證 | 正則 `^[0-9A-Za-z]{1,10}$` |
| **低** | TWSESource | 每次建立新 httpx.AsyncClient | 共用 client |

---

# Part 4: 建議測試工具

| 層 | 工具 | 用途 |
|----|------|------|
| Backend 單元測試 | pytest + pytest-asyncio | DataSource、Indicator、AI Analyzer |
| Backend 整合測試 | testcontainers (PostgreSQL) | DB 層端到端 |
| Frontend 單元測試 | Jest + React Testing Library | 元件渲染、狀態、事件 |
| Frontend Mock API | MSW (Mock Service Worker) | 各種 API 回應場景 |
| E2E 測試 | Playwright | 完整使用者流程、responsive |
| Plugin 測試 | bash + sqlite3 | Hook 腳本功能驗證 |
