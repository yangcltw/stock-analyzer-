# 台股技術分析系統

輸入台股代號，查看近 30 個交易日的 K 線走勢圖、MA5/MA20 均線、AI 趨勢分析。

## 快速啟動

**需求:** Docker + Docker Compose

```bash
git clone <repo-url>
cd scratchProject
./start.sh
```

或手動：

```bash
cp .env.example .env        # 編輯 .env 填入 API keys
docker-compose up --build    # 啟動所有服務
```

打開 http://localhost:3000，輸入股票代號（例如 2330）。

## 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `GEMINI_API_KEY` | 建議 | Google Gemini API key（AI 分析主要來源） |
| `OPENAI_API_KEY` | 選填 | OpenAI API key（AI 分析備援） |
| `DATABASE_URL` | 自動 | PostgreSQL 連線（Docker 內自動設定） |
| `CORS_ORIGINS` | 選填 | 允許的前端來源（預設 `http://localhost:3000`） |

不填 API key 也能使用 — 圖表和數據正常顯示，只是沒有 AI 分析。

## 技術棧

- **Frontend:** Next.js + TradingView Lightweight Charts + Tailwind CSS
- **Backend:** Python FastAPI + asyncpg + yfinance
- **AI:** Gemini 2.5 Flash → OpenAI GPT-4o-mini（fallback）
- **Data:** yfinance → TWSE 證交所（fallback）→ PostgreSQL（持久化）
- **Infra:** Docker Compose（3 containers）

## 常用指令

```bash
docker-compose up --build -d   # 啟動
docker-compose down            # 停止
docker-compose logs -f backend # 查看後端 log
docker-compose restart backend # 重啟後端（改 .env 後需 down/up）
```
