# Taiwan Stock Technical Analyzer - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web system that displays Taiwan stock price charts with MA5/MA20 and AI trend analysis.

**Architecture:** Next.js frontend calls a FastAPI backend. Backend fetches 49 trading days from yfinance (TWSE fallback), stores in PostgreSQL, calculates MA5/MA20, generates AI analysis via OpenAI. Three-layer data flow: memory cache → DB → external API.

**Tech Stack:** Next.js, React, TradingView Lightweight Charts, Python FastAPI, PostgreSQL, asyncpg, yfinance, OpenAI SDK, Docker Compose

**Spec:** `docs/superpowers/specs/2026-03-30-tw-stock-analyzer-design.md`

---

## Execution Strategy: Module-Based Parallel Agents

```
                    ┌──────────────────┐
                    │ Module 1:        │
                    │ Infrastructure   │
                    └────────┬─────────┘
                             │ 完成後平行展開
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐
│ Module 2:       │ │ Module 3:     │ │ Module 4:       │
│ Data Layer      │ │ Business Logic│ │ Frontend        │
└────────┬────────┘ └──────┬────────┘ └────────┬────────┘
         └─────────────────┼────────────────────┘
                           ▼
                 ┌─────────────────────┐
                 │ Module 5:           │
                 │ Integration         │
                 └─────────────────────┘
```

| Module | Agent | 可平行 | 依賴 |
|--------|-------|--------|------|
| 1. Infrastructure | Infra Agent | - | 無 |
| 2. Data Layer | Data Agent | 是 | Module 1 |
| 3. Business Logic | Logic Agent | 是 | Module 1 |
| 4. Frontend | Frontend Agent | 是 | Module 1 |
| 5. Integration | Integration Agent | 否 | Module 2+3+4 |

---

## Module 1: Infrastructure Agent

**職責:** 專案骨架、Docker Compose、基礎設定

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `frontend/Dockerfile`
- Create: `frontend/next.config.js`

### Task 1.1: Root Config Files

- [ ] **Step 1: Create `.gitignore`**

```
node_modules/
__pycache__/
.env
.next/
pgdata/
*.pyc
.pytest_cache/
```

- [ ] **Step 2: Create `.env.example`**

```
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://postgres:postgres@db:5432/stockdb
CORS_ORIGINS=http://localhost:3000
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  frontend:
    build:
      context: ./frontend
      args:
        - NEXT_PUBLIC_API_URL=http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/stockdb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=stockdb
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

- [ ] **Step 4: Commit**

```bash
git init
git add .gitignore .env.example docker-compose.yml
git commit -m "feat: root config files and Docker Compose"
```

### Task 1.2: Backend Skeleton

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
asyncpg==0.30.0
yfinance==0.2.40
httpx==0.27.0
openai==1.50.0
pydantic-settings==2.5.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create `backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
```

- [ ] **Step 3: Create `backend/app/__init__.py`**

Empty file.

- [ ] **Step 4: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/stockdb"
    openai_api_key: str = ""
    cache_ttl_default: int = 3600
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 5: Create `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: DB pool initialized in Module 2
    yield
    # Shutdown: cleanup in Module 2


app = FastAPI(title="TW Stock Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 7: Create `backend/tests/__init__.py`**

Empty file.

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: backend skeleton with FastAPI and config"
```

### Task 1.3: Frontend Skeleton

- [ ] **Step 1: Scaffold Next.js project**

```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

- [ ] **Step 2: Update `frontend/next.config.js` to enable standalone output**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};

module.exports = nextConfig;
```

- [ ] **Step 3: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
```

- [ ] **Step 4: Verify Docker Compose starts**

```bash
docker-compose up --build
```

Expected: All 3 containers start. `http://localhost:8000/health` returns `{"status": "ok"}`. `http://localhost:3000` shows Next.js default page.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: frontend skeleton with Next.js, standalone Dockerfile, and next.config"
```

---

## Module 2: Data Layer Agent

**職責:** DataSource 介面、所有資料源實作（yfinance, TWSE, DB, cache, fallback）

**依賴:** Module 1 完成

**Files:**
- Create: `backend/app/datasources/__init__.py`
- Create: `backend/app/datasources/models.py`
- Create: `backend/app/datasources/interface.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/connection.py`
- Create: `backend/app/db/migrations.py`
- Create: `backend/app/datasources/yfinance_source.py`
- Create: `backend/app/datasources/twse_source.py`
- Create: `backend/app/datasources/db_source.py`
- Create: `backend/app/datasources/fallback_source.py`
- Create: `backend/app/datasources/cached_source.py`
- Create: `backend/tests/test_yfinance_source.py`
- Create: `backend/tests/test_twse_source.py`
- Create: `backend/tests/test_db_source.py`
- Create: `backend/tests/test_fallback_source.py`
- Create: `backend/tests/test_cached_source.py`

### Task 2.1: DataSource Interface + Models

- [ ] **Step 1: Create `backend/app/datasources/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backend/app/datasources/models.py`**

```python
from dataclasses import dataclass


@dataclass
class StockDailyData:
    date: str       # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int
```

- [ ] **Step 3: Create `backend/app/datasources/interface.py`**

```python
from abc import ABC, abstractmethod

from app.datasources.models import StockDailyData


class StockDataSource(ABC):
    @abstractmethod
    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        """Fetch daily stock data.

        Args:
            symbol: Taiwan stock symbol (digits only, e.g. "2330").
            count: Number of trading day rows to return.
        """
        ...
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/datasources/
git commit -m "feat: DataSource interface and StockDailyData model"
```

### Task 2.2: Database Connection + Schema

- [ ] **Step 1: Create `backend/app/db/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backend/app/db/connection.py`**

```python
import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

- [ ] **Step 3: Create `backend/app/db/migrations.py`**

```python
from app.db.connection import get_pool


async def run_migrations():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily_data (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                date DATE NOT NULL,
                open DECIMAL(10,2) NOT NULL,
                high DECIMAL(10,2) NOT NULL,
                low DECIMAL(10,2) NOT NULL,
                close DECIMAL(10,2) NOT NULL,
                volume BIGINT NOT NULL,
                fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(symbol, date)
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_daily_symbol_date
            ON stock_daily_data(symbol, date DESC)
        """)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/db/
git commit -m "feat: asyncpg connection pool and DB schema migration"
```

### Task 2.3: YFinance DataSource

- [ ] **Step 1: Write test `backend/tests/test_yfinance_source.py`**

```python
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from app.datasources.yfinance_source import YFinanceSource


def _mock_dataframe(n: int) -> pd.DataFrame:
    dates = pd.date_range("2026-03-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(n)],
            "High": [105.0 + i for i in range(n)],
            "Low": [95.0 + i for i in range(n)],
            "Close": [102.0 + i for i in range(n)],
            "Volume": [1000 * (i + 1) for i in range(n)],
        },
        index=dates,
    )


@pytest.mark.asyncio
async def test_yfinance_returns_stock_data():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_dataframe(5)

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        result = await source.get_daily_data("2330", 5)

    assert len(result) == 5
    assert result[0].open == 100.0
    assert result[0].close == 102.0


@pytest.mark.asyncio
async def test_yfinance_appends_tw_suffix():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_dataframe(5)

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker) as mock_cls:
        await source.get_daily_data("2330", 5)

    mock_cls.assert_called_once_with("2330.TW")


@pytest.mark.asyncio
async def test_yfinance_raises_on_empty_data():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(ValueError, match="No data"):
            await source.get_daily_data("9999", 5)


@pytest.mark.asyncio
async def test_yfinance_get_stock_name():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.info = {"longName": "Taiwan Semiconductor"}

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        name = await source.get_stock_name("2330")

    assert name == "Taiwan Semiconductor"


@pytest.mark.asyncio
async def test_yfinance_get_stock_name_fallback():
    source = YFinanceSource()
    mock_ticker = MagicMock()
    mock_ticker.info = {}

    with patch("app.datasources.yfinance_source.yf.Ticker", return_value=mock_ticker):
        name = await source.get_stock_name("2330")

    assert name == "2330"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_yfinance_source.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement `backend/app/datasources/yfinance_source.py`**

```python
import asyncio
from functools import partial

import yfinance as yf

from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData


class YFinanceSource(StockDataSource):
    def __init__(self):
        self._name_cache: dict[str, str] = {}

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        loop = asyncio.get_running_loop()
        df = await loop.run_in_executor(None, partial(self._fetch, symbol, count))

        if df.empty:
            raise ValueError(f"No data returned for symbol {symbol}")

        return [
            StockDailyData(
                date=index.strftime("%Y-%m-%d"),
                open=round(float(row["Open"]), 2),
                high=round(float(row["High"]), 2),
                low=round(float(row["Low"]), 2),
                close=round(float(row["Close"]), 2),
                volume=int(row["Volume"]),
            )
            for index, row in df.iterrows()
        ]

    async def get_stock_name(self, symbol: str) -> str:
        if symbol in self._name_cache:
            return self._name_cache[symbol]

        loop = asyncio.get_running_loop()
        name = await loop.run_in_executor(None, partial(self._fetch_name, symbol))
        self._name_cache[symbol] = name
        return name

    def _fetch(self, symbol: str, count: int):
        ticker = yf.Ticker(f"{symbol}.TW")
        return ticker.history(period=f"{count * 2}d").tail(count)

    def _fetch_name(self, symbol: str) -> str:
        ticker = yf.Ticker(f"{symbol}.TW")
        return ticker.info.get("longName", symbol)
```

- [ ] **Step 4: Run test**

```bash
cd backend && python -m pytest tests/test_yfinance_source.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/datasources/yfinance_source.py backend/tests/test_yfinance_source.py
git commit -m "feat: yfinance data source for Taiwan stocks with name lookup"
```

### Task 2.4: TWSE Fallback DataSource

- [ ] **Step 1: Write test `backend/tests/test_twse_source.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.datasources.twse_source import TWSESource


def _mock_twse_response():
    """Mock TWSE STOCK_DAY API response.

    Real TWSE STOCK_DAY column order:
    [0] 日期, [1] 成交股數, [2] 成交金額, [3] 開盤價, [4] 最高價,
    [5] 最低價, [6] 收盤價, [7] 漲跌價差, [8] 成交筆數

    Note: 成交股數 ([1]) is in shares, not lots. For example,
    "35,185,922" means 35,185,922 shares.
    """
    return {
        "stat": "OK",
        "data": [
            ["115/03/02", "35,185,922", "15,500,000,000", "890.00", "895.00", "885.00", "892.00", "+5.00", "12,345"],
            ["115/03/03", "40,210,388", "18,000,000,000", "892.00", "900.00", "890.00", "898.00", "+6.00", "15,678"],
        ],
    }


@pytest.mark.asyncio
async def test_twse_parses_response():
    source = TWSESource()

    with patch.object(source, "_fetch_month", new_callable=AsyncMock, return_value=_mock_twse_response()):
        result = await source.get_daily_data("2330", 2)

    assert len(result) == 2
    assert result[0].close == 892.0
    # Volume is in shares (成交股數), parsed directly from column [1]
    assert result[0].volume == 35185922


@pytest.mark.asyncio
async def test_twse_converts_roc_date():
    source = TWSESource()

    with patch.object(source, "_fetch_month", new_callable=AsyncMock, return_value=_mock_twse_response()):
        result = await source.get_daily_data("2330", 2)

    assert result[0].date == "2026-03-02"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_twse_source.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement `backend/app/datasources/twse_source.py`**

```python
from datetime import date, timedelta

import httpx

from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData


class TWSESource(StockDataSource):
    """TWSE STOCK_DAY API data source.

    Real TWSE STOCK_DAY column order:
    [0] 日期, [1] 成交股數, [2] 成交金額, [3] 開盤價, [4] 最高價,
    [5] 最低價, [6] 收盤價, [7] 漲跌價差, [8] 成交筆數

    Note: 成交股數 ([1]) is in shares (not lots). e.g. "35,185,922" = 35,185,922 shares.
    """

    BASE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        all_data: list[StockDailyData] = []
        current = date.today()

        for _ in range(3):
            resp = await self._fetch_month(symbol, current.year, current.month)
            if resp and resp.get("stat") == "OK" and resp.get("data"):
                parsed = self._parse_rows(resp["data"])
                all_data = parsed + all_data
            current = (current.replace(day=1) - timedelta(days=1))

        if not all_data:
            raise ValueError(f"No data from TWSE for symbol {symbol}")

        return all_data[-count:]

    async def _fetch_month(self, symbol: str, year: int, month: int) -> dict | None:
        date_str = f"{year}{month:02d}01"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.BASE_URL,
                params={"response": "json", "date": date_str, "stockNo": symbol},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
        return None

    def _parse_rows(self, rows: list[list[str]]) -> list[StockDailyData]:
        result = []
        for row in rows:
            try:
                # [0] 日期 in ROC format: "115/03/02"
                parts = row[0].strip().split("/")
                y = int(parts[0]) + 1911
                m = int(parts[1])
                d = int(parts[2])

                # [1] 成交股數 — volume in shares (e.g. "35,185,922")
                volume = int(row[1].replace(",", ""))

                result.append(StockDailyData(
                    date=f"{y}-{m:02d}-{d:02d}",
                    open=float(row[3].replace(",", "")),
                    high=float(row[4].replace(",", "")),
                    low=float(row[5].replace(",", "")),
                    close=float(row[6].replace(",", "")),
                    volume=volume,
                ))
            except (ValueError, IndexError):
                continue
        return result
```

- [ ] **Step 4: Run test**

```bash
cd backend && python -m pytest tests/test_twse_source.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/datasources/twse_source.py backend/tests/test_twse_source.py
git commit -m "feat: TWSE fallback data source with ROC date conversion"
```

### Task 2.5: Fallback DataSource Decorator

- [ ] **Step 1: Write test `backend/tests/test_fallback_source.py`**

```python
import pytest
from unittest.mock import AsyncMock

from app.datasources.models import StockDailyData
from app.datasources.fallback_source import FallbackDataSource


def _make_data(n: int) -> list[StockDailyData]:
    return [
        StockDailyData(date=f"2026-03-{i+1:02d}", open=100.0, high=105.0, low=95.0, close=102.0, volume=1000)
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_uses_primary_when_available():
    primary = AsyncMock()
    primary.get_daily_data.return_value = _make_data(5)
    fallback = AsyncMock()

    source = FallbackDataSource(primary, fallback)
    result = await source.get_daily_data("2330", 5)

    assert len(result) == 5
    fallback.get_daily_data.assert_not_called()


@pytest.mark.asyncio
async def test_switches_on_primary_error():
    primary = AsyncMock()
    primary.get_daily_data.side_effect = Exception("yfinance down")
    fallback = AsyncMock()
    fallback.get_daily_data.return_value = _make_data(5)

    source = FallbackDataSource(primary, fallback)
    result = await source.get_daily_data("2330", 5)

    assert len(result) == 5
    fallback.get_daily_data.assert_called_once()


@pytest.mark.asyncio
async def test_raises_when_all_fail():
    primary = AsyncMock()
    primary.get_daily_data.side_effect = Exception("yfinance down")
    fallback = AsyncMock()
    fallback.get_daily_data.side_effect = Exception("TWSE down")

    source = FallbackDataSource(primary, fallback)
    with pytest.raises(Exception, match="TWSE down"):
        await source.get_daily_data("2330", 5)
```

- [ ] **Step 2: Implement `backend/app/datasources/fallback_source.py`**

```python
from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData


class FallbackDataSource(StockDataSource):
    def __init__(self, primary: StockDataSource, fallback: StockDataSource):
        self._primary = primary
        self._fallback = fallback

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        try:
            return await self._primary.get_daily_data(symbol, count)
        except Exception:
            return await self._fallback.get_daily_data(symbol, count)
```

- [ ] **Step 3: Run test**

```bash
cd backend && python -m pytest tests/test_fallback_source.py -v
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/datasources/fallback_source.py backend/tests/test_fallback_source.py
git commit -m "feat: fallback data source decorator with auto-failover"
```

### Task 2.6: Database DataSource

- [ ] **Step 1: Write test `backend/tests/test_db_source.py`**

```python
import pytest
from unittest.mock import AsyncMock

from app.datasources.models import StockDailyData
from app.datasources.db_source import DatabaseDataSource


def _make_data(n: int) -> list[StockDailyData]:
    return [
        StockDailyData(
            date=f"2026-03-{i+1:02d}", open=100.0+i, high=105.0+i,
            low=95.0+i, close=102.0+i, volume=1000*(i+1),
        )
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_delegates_to_upstream_when_db_fresh_empty(monkeypatch):
    """When _read_fresh_from_db returns empty, fetch from upstream."""
    upstream = AsyncMock()
    upstream.get_daily_data.return_value = _make_data(5)
    source = DatabaseDataSource(upstream)

    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_read_stale_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_write_to_db", AsyncMock())
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 5
    upstream.get_daily_data.assert_called_once()


@pytest.mark.asyncio
async def test_returns_fresh_db_data_when_sufficient(monkeypatch):
    """When _read_fresh_from_db returns enough rows, skip upstream."""
    upstream = AsyncMock()
    source = DatabaseDataSource(upstream)

    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=_make_data(5)))
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 5
    upstream.get_daily_data.assert_not_called()


@pytest.mark.asyncio
async def test_returns_stale_db_data_when_upstream_fails(monkeypatch):
    """When upstream fails, _read_stale_from_db is used as last resort."""
    upstream = AsyncMock()
    upstream.get_daily_data.side_effect = Exception("all APIs down")
    source = DatabaseDataSource(upstream)

    stale = _make_data(3)
    monkeypatch.setattr(source, "_read_fresh_from_db", AsyncMock(return_value=[]))
    monkeypatch.setattr(source, "_read_stale_from_db", AsyncMock(return_value=stale))
    monkeypatch.setattr(source, "_write_to_db", AsyncMock())
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 3  # stale data returned


@pytest.mark.asyncio
async def test_fresh_path_uses_freshness_filter(monkeypatch):
    """Verify _read_fresh_from_db is called (not _read_stale_from_db) on happy path."""
    upstream = AsyncMock()
    source = DatabaseDataSource(upstream)

    fresh_mock = AsyncMock(return_value=_make_data(5))
    stale_mock = AsyncMock(return_value=_make_data(5))
    monkeypatch.setattr(source, "_read_fresh_from_db", fresh_mock)
    monkeypatch.setattr(source, "_read_stale_from_db", stale_mock)
    monkeypatch.setattr("app.datasources.db_source.get_pool", AsyncMock())

    result = await source.get_daily_data("2330", 5)
    assert len(result) == 5
    fresh_mock.assert_called_once()
    stale_mock.assert_not_called()
```

- [ ] **Step 2: Implement `backend/app/datasources/db_source.py`**

```python
from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData
from app.db.connection import get_pool


class DatabaseDataSource(StockDataSource):
    def __init__(self, upstream: StockDataSource, freshness_hours: int = 24):
        self._upstream = upstream
        self._freshness_hours = freshness_hours

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        pool = await get_pool()

        # Try fresh data first (within freshness_hours)
        rows = await self._read_fresh_from_db(pool, symbol, count)
        if len(rows) >= count:
            return rows[:count]

        # Fresh data insufficient — fetch from upstream
        try:
            data = await self._upstream.get_daily_data(symbol, count)
            await self._write_to_db(pool, symbol, data)
            return data
        except Exception:
            # Upstream failed — fall back to stale DB data (no freshness filter)
            stale_rows = await self._read_stale_from_db(pool, symbol, count)
            if stale_rows:
                return stale_rows
            raise

    async def _read_fresh_from_db(self, pool, symbol: str, count: int) -> list[StockDailyData]:
        """Read rows that have been fetched within freshness_hours."""
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT date, open, high, low, close, volume
                FROM stock_daily_data
                WHERE symbol = $1
                  AND fetched_at > NOW() - INTERVAL '1 hour' * $3
                ORDER BY date DESC
                LIMIT $2
                """,
                symbol, count, self._freshness_hours
            )
        return [
            StockDailyData(
                date=row["date"].isoformat(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )
            for row in reversed(rows)
        ]

    async def _read_stale_from_db(self, pool, symbol: str, count: int) -> list[StockDailyData]:
        """Read rows regardless of freshness (last resort fallback)."""
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT date, open, high, low, close, volume
                FROM stock_daily_data
                WHERE symbol = $1
                ORDER BY date DESC
                LIMIT $2
                """,
                symbol, count
            )
        return [
            StockDailyData(
                date=row["date"].isoformat(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )
            for row in reversed(rows)
        ]

    async def _write_to_db(self, pool, symbol: str, data: list[StockDailyData]):
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO stock_daily_data (symbol, date, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    open = EXCLUDED.open, high = EXCLUDED.high,
                    low = EXCLUDED.low, close = EXCLUDED.close,
                    volume = EXCLUDED.volume, fetched_at = NOW()
                """,
                [(symbol, d.date, d.open, d.high, d.low, d.close, d.volume) for d in data],
            )
```

- [ ] **Step 3: Run test**

```bash
cd backend && python -m pytest tests/test_db_source.py -v
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/datasources/db_source.py backend/tests/test_db_source.py
git commit -m "feat: database data source with freshness check and stale fallback"
```

### Task 2.7: Cached DataSource Decorator

**Note:** This task depends on `app.utils.cache_ttl` from Module 3. If Module 3 is not yet complete, use a stub: `def get_ttl_seconds(): return 3600`. Replace with real import when Module 3 lands.

- [ ] **Step 1: Write test `backend/tests/test_cached_source.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.datasources.models import StockDailyData
from app.datasources.cached_source import CachedDataSource


def _make_data(n: int) -> list[StockDailyData]:
    return [
        StockDailyData(date=f"2026-03-{i+1:02d}", open=100.0, high=105.0, low=95.0, close=102.0, volume=1000)
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_returns_cache_on_second_call():
    upstream = AsyncMock()
    upstream.get_daily_data.return_value = _make_data(5)

    with patch("app.datasources.cached_source.get_ttl_seconds", return_value=3600):
        source = CachedDataSource(upstream)
        await source.get_daily_data("2330", 5)
        await source.get_daily_data("2330", 5)

    upstream.get_daily_data.assert_called_once()


@pytest.mark.asyncio
async def test_different_symbols_not_shared():
    upstream = AsyncMock()
    upstream.get_daily_data.return_value = _make_data(5)

    with patch("app.datasources.cached_source.get_ttl_seconds", return_value=3600):
        source = CachedDataSource(upstream)
        await source.get_daily_data("2330", 5)
        await source.get_daily_data("2317", 5)

    assert upstream.get_daily_data.call_count == 2


@pytest.mark.asyncio
async def test_cache_expires_after_ttl():
    """Verify that upstream is called again after TTL expires."""
    upstream = AsyncMock()
    upstream.get_daily_data.return_value = _make_data(5)

    fake_time = [1000.0]

    def mock_time():
        return fake_time[0]

    with patch("app.datasources.cached_source.get_ttl_seconds", return_value=60), \
         patch("app.datasources.cached_source.time") as mock_time_module:
        mock_time_module.time = mock_time

        source = CachedDataSource(upstream)

        # First call — fetches from upstream
        await source.get_daily_data("2330", 5)
        assert upstream.get_daily_data.call_count == 1

        # Second call — still within TTL, should use cache
        fake_time[0] = 1050.0
        await source.get_daily_data("2330", 5)
        assert upstream.get_daily_data.call_count == 1

        # Third call — past TTL (1000 + 60 = 1060), should fetch again
        fake_time[0] = 1070.0
        await source.get_daily_data("2330", 5)
        assert upstream.get_daily_data.call_count == 2
```

- [ ] **Step 2: Implement `backend/app/datasources/cached_source.py`**

```python
import asyncio
import time

from app.datasources.interface import StockDataSource
from app.datasources.models import StockDailyData
from app.utils.cache_ttl import get_ttl_seconds


class CachedDataSource(StockDataSource):
    def __init__(self, upstream: StockDataSource):
        self._upstream = upstream
        self._cache: dict[str, tuple[list[StockDailyData], float]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        cache_key = f"{symbol}_{count}"

        if cache_key in self._cache:
            data, expires_at = self._cache[cache_key]
            if time.time() < expires_at:
                return data

        # Use setdefault which is atomic in CPython — avoids race on lock creation
        lock = self._locks.setdefault(cache_key, asyncio.Lock())

        async with lock:
            # Double-check after acquiring lock
            if cache_key in self._cache:
                data, expires_at = self._cache[cache_key]
                if time.time() < expires_at:
                    return data

            data = await self._upstream.get_daily_data(symbol, count)
            ttl = get_ttl_seconds()
            self._cache[cache_key] = (data, time.time() + ttl)
            return data
```

- [ ] **Step 3: Run test**

```bash
cd backend && python -m pytest tests/test_cached_source.py -v
```

Expected: All PASS

- [ ] **Step 4: Run all Data Layer tests**

```bash
cd backend && python -m pytest tests/test_yfinance_source.py tests/test_twse_source.py tests/test_db_source.py tests/test_fallback_source.py tests/test_cached_source.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/datasources/cached_source.py backend/tests/test_cached_source.py
git commit -m "feat: cached data source with smart TTL, lock cleanup, and expiry test"
```

---

## Module 3: Business Logic Agent

**職責:** 交易日曆、Cache TTL、MA 計算、AI 分析

**依賴:** Module 1 完成

**Files:**
- Create: `backend/holidays/2026.json`
- Create: `backend/app/utils/__init__.py`
- Create: `backend/app/utils/trading_calendar.py`
- Create: `backend/app/utils/cache_ttl.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/indicator.py`
- Create: `backend/app/services/ai_analyzer.py`
- Create: `backend/tests/test_trading_calendar.py`
- Create: `backend/tests/test_cache_ttl.py`
- Create: `backend/tests/test_indicator.py`
- Create: `backend/tests/test_ai_analyzer.py`

### Task 3.1: Trading Calendar

- [ ] **Step 1: Create `backend/holidays/2026.json`**

```json
[
  "2026-01-01", "2026-01-02",
  "2026-01-26", "2026-01-27", "2026-01-28", "2026-01-29", "2026-01-30",
  "2026-02-23",
  "2026-04-03", "2026-04-06",
  "2026-05-01", "2026-05-25",
  "2026-06-19",
  "2026-09-21",
  "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"
]
```

- [ ] **Step 2: Write test `backend/tests/test_trading_calendar.py`**

```python
from datetime import datetime, date
from zoneinfo import ZoneInfo

from app.utils.trading_calendar import is_trading_day, get_next_trading_day_open

TW = ZoneInfo("Asia/Taipei")


def test_weekday_is_trading_day():
    assert is_trading_day(date(2026, 3, 30)) is True


def test_saturday_is_not_trading_day():
    assert is_trading_day(date(2026, 3, 28)) is False


def test_sunday_is_not_trading_day():
    assert is_trading_day(date(2026, 3, 29)) is False


def test_holiday_is_not_trading_day():
    assert is_trading_day(date(2026, 1, 1)) is False


def test_next_trading_day_from_friday_afternoon():
    now = datetime(2026, 3, 27, 14, 0, tzinfo=TW)
    result = get_next_trading_day_open(now)
    assert result == datetime(2026, 3, 30, 9, 0, tzinfo=TW)


def test_next_trading_day_from_weekday_morning():
    now = datetime(2026, 3, 30, 10, 0, tzinfo=TW)
    result = get_next_trading_day_open(now)
    assert result == datetime(2026, 3, 31, 9, 0, tzinfo=TW)


def test_next_trading_day_from_saturday():
    now = datetime(2026, 3, 28, 12, 0, tzinfo=TW)
    result = get_next_trading_day_open(now)
    assert result == datetime(2026, 3, 30, 9, 0, tzinfo=TW)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_trading_calendar.py -v
```

Expected: FAIL

- [ ] **Step 4: Create `backend/app/utils/__init__.py`**

Empty file.

- [ ] **Step 5: Implement `backend/app/utils/trading_calendar.py`**

```python
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TW_TZ = ZoneInfo("Asia/Taipei")

logger = logging.getLogger(__name__)

_holidays: set[date] | None = None


def _load_holidays() -> set[date]:
    global _holidays
    if _holidays is not None:
        return _holidays
    holidays_dir = Path(__file__).parent.parent.parent / "holidays"
    _holidays = set()
    for json_file in holidays_dir.glob("*.json"):
        with open(json_file) as f:
            dates = json.load(f)
            _holidays.update(date.fromisoformat(d) for d in dates)

    current_year = date.today().year
    if not any(d.year == current_year for d in _holidays):
        logger.warning(
            f"No holiday data for {current_year}. "
            "All weekdays will be treated as trading days."
        )

    return _holidays


def is_trading_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d not in _load_holidays()


def get_next_trading_day_open(now: datetime) -> datetime:
    current = now.astimezone(TW_TZ).date() + timedelta(days=1)
    while not is_trading_day(current):
        current += timedelta(days=1)
    return datetime(current.year, current.month, current.day, 9, 0, tzinfo=TW_TZ)
```

- [ ] **Step 6: Run test**

```bash
cd backend && python -m pytest tests/test_trading_calendar.py -v
```

Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/holidays/ backend/app/utils/ backend/tests/test_trading_calendar.py
git commit -m "feat: Taiwan stock trading calendar with holiday support and missing-year warning"
```

### Task 3.2: Cache TTL

- [ ] **Step 1: Write test `backend/tests/test_cache_ttl.py`**

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from app.utils.cache_ttl import get_ttl_seconds

TW = ZoneInfo("Asia/Taipei")


def test_ttl_during_trading_hours():
    now = datetime(2026, 3, 30, 10, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 12600  # until 13:30


def test_ttl_after_close():
    now = datetime(2026, 3, 30, 14, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 68400  # until next day 09:00


def test_ttl_friday_after_close():
    now = datetime(2026, 3, 27, 14, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 241200  # until Monday 09:00


def test_ttl_saturday():
    now = datetime(2026, 3, 28, 12, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 162000  # until Monday 09:00


def test_ttl_before_market_open():
    """At 08:00 on a trading day, TTL should last until 13:30 (market close).

    Data won't change until market closes, so cache until 13:30.
    From 08:00 to 13:30 = 5.5 hours = 19800 seconds.
    """
    now = datetime(2026, 3, 30, 8, 0, tzinfo=TW)
    assert get_ttl_seconds(now) == 19800  # until 13:30
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_cache_ttl.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement `backend/app/utils/cache_ttl.py`**

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from app.utils.trading_calendar import TW_TZ, is_trading_day, get_next_trading_day_open

MARKET_CLOSE_HOUR = 13
MARKET_CLOSE_MINUTE = 30


def get_ttl_seconds(now: datetime | None = None) -> int:
    if now is None:
        now = datetime.now(TW_TZ)
    else:
        now = now.astimezone(TW_TZ)

    today = now.date()

    if is_trading_day(today):
        market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
        if now < market_close:
            return int((market_close - now).total_seconds())

    next_open = get_next_trading_day_open(now)
    return int((next_open - now).total_seconds())
```

- [ ] **Step 4: Run test**

```bash
cd backend && python -m pytest tests/test_cache_ttl.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/cache_ttl.py backend/tests/test_cache_ttl.py
git commit -m "feat: smart cache TTL based on market hours and trading calendar"
```

### Task 3.3: MA Indicator Service

- [ ] **Step 1: Write test `backend/tests/test_indicator.py`**

```python
from app.services.indicator import IndicatorService


def test_ma5_basic():
    prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    result = IndicatorService.calculate_ma(prices, 5)
    assert result[0] is None
    assert result[3] is None
    assert result[4] == 12.0
    assert result[5] == 13.0
    assert result[6] == 14.0


def test_ma20_needs_20_points():
    prices = [float(i) for i in range(25)]
    result = IndicatorService.calculate_ma(prices, 20)
    assert all(v is None for v in result[:19])
    assert result[19] == sum(range(20)) / 20


def test_ma_empty_list():
    assert IndicatorService.calculate_ma([], 5) == []


def test_ma_fewer_than_period():
    prices = [1.0, 2.0, 3.0]
    result = IndicatorService.calculate_ma(prices, 5)
    assert all(v is None for v in result)
    assert len(result) == 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_indicator.py -v
```

Expected: FAIL

- [ ] **Step 3: Create `backend/app/services/__init__.py`**

Empty file.

- [ ] **Step 4: Implement `backend/app/services/indicator.py`**

```python
class IndicatorService:
    @staticmethod
    def calculate_ma(prices: list[float], period: int) -> list[float | None]:
        result: list[float | None] = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(None)
            else:
                window = prices[i - period + 1 : i + 1]
                result.append(round(sum(window) / period, 2))
        return result
```

- [ ] **Step 5: Run test**

```bash
cd backend && python -m pytest tests/test_indicator.py -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ backend/tests/test_indicator.py
git commit -m "feat: MA calculation service with sliding window"
```

### Task 3.4: AI Analyzer (OpenAI)

- [ ] **Step 1: Write test `backend/tests/test_ai_analyzer.py`**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_ai_analyzer.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement `backend/app/services/ai_analyzer.py`**

```python
from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from app.config import settings
from app.datasources.models import StockDailyData


class AIAnalyzer(ABC):
    @abstractmethod
    async def analyze(
        self, symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]
    ) -> str | None:
        ...


class OpenAIAnalyzer(AIAnalyzer):
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(
        self, symbol: str, data: list[StockDailyData], ma5: list[float], ma20: list[float]
    ) -> str | None:
        try:
            prices_text = "\n".join(
                f"{d.date}: 開={d.open} 高={d.high} 低={d.low} 收={d.close} 量={d.volume}"
                for d in data
            )
            ma_text = (
                f"MA5 最新值: {ma5[-1]}, MA20 最新值: {ma20[-1]}\n"
                f"MA5 趨勢: {ma5[-5:]}\nMA20 趨勢: {ma20[-5:]}"
            )

            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一位台股技術分析助手。請根據提供的實際股價數據和均線數據，"
                            "用繁體中文描述股價趨勢。你必須：\n"
                            "1. 只根據實際數據描述趨勢\n"
                            "2. 絕對不可以提供任何投資建議\n"
                            "3. 不可以建議買入、賣出或持有\n"
                            "4. 回覆限制在 200 字以內"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"股票代號: {symbol}\n\n近期股價資料:\n{prices_text}\n\n均線資料:\n{ma_text}",
                    },
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content
        except Exception:
            return None
```

- [ ] **Step 4: Run test**

```bash
cd backend && python -m pytest tests/test_ai_analyzer.py -v
```

Expected: All PASS

- [ ] **Step 5: Run all Module 3 tests**

```bash
cd backend && python -m pytest tests/test_trading_calendar.py tests/test_cache_ttl.py tests/test_indicator.py tests/test_ai_analyzer.py -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ai_analyzer.py backend/tests/test_ai_analyzer.py
git commit -m "feat: OpenAI analyzer with graceful degradation"
```

---

## Module 4: Frontend Agent

**職責:** 所有 React 元件、TradingView 圖表、API service

**依賴:** Module 1 完成

**Files:**
- Create: `frontend/src/types/stock.ts`
- Create: `frontend/src/services/stockApi.ts`
- Create: `frontend/src/components/StockInput.tsx`
- Create: `frontend/src/components/StockChart.tsx`
- Create: `frontend/src/components/AIAnalysis.tsx`
- Modify: `frontend/src/app/page.tsx`

### Task 4.1: Types + API Service

- [ ] **Step 1: Create `frontend/src/types/stock.ts`**

```typescript
export interface StockDailyData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockResponse {
  symbol: string;
  name: string | null;
  data: StockDailyData[];
  ma5: (number | null)[];
  ma20: (number | null)[];
  ai_analysis: string | null;
}
```

- [ ] **Step 2: Create `frontend/src/services/stockApi.ts`**

```typescript
import { StockResponse } from "@/types/stock";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchStock(symbol: string): Promise<StockResponse> {
  const res = await fetch(`${API_URL}/api/stock/${symbol}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/ frontend/src/services/
git commit -m "feat: frontend types and API service"
```

### Task 4.2: StockInput Component

- [ ] **Step 1: Create `frontend/src/components/StockInput.tsx`**

```tsx
"use client";

import { useState } from "react";

interface StockInputProps {
  onSearch: (symbol: string) => void;
  loading: boolean;
  error: string | null;
}

export default function StockInput({ onSearch, loading, error }: StockInputProps) {
  const [symbol, setSymbol] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = symbol.trim();
    if (trimmed) {
      onSearch(trimmed);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-center">
      <input
        type="text"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        placeholder="輸入台股代號 (例: 2330)"
        className="border rounded px-3 py-2 text-lg w-48"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !symbol.trim()}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "查詢中..." : "查詢"}
      </button>
      {error && <span className="text-red-500 text-sm">{error}</span>}
    </form>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/StockInput.tsx
git commit -m "feat: stock symbol input component"
```

### Task 4.3: StockChart Component

- [ ] **Step 1: Install TradingView Lightweight Charts**

```bash
cd frontend && npm install lightweight-charts
```

- [ ] **Step 2: Create `frontend/src/components/StockChart.tsx`**

```tsx
"use client";

import { useEffect, useRef } from "react";
import { createChart, IChartApi, LineSeries, CandlestickSeries } from "lightweight-charts";
import { StockResponse } from "@/types/stock";

interface StockChartProps {
  data: StockResponse;
}

export default function StockChart({ data }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#333",
      },
      grid: {
        vertLines: { color: "#e0e0e0" },
        horzLines: { color: "#e0e0e0" },
      },
      timeScale: {
        timeVisible: false,
        borderColor: "#ccc",
      },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#ef5350",
      downColor: "#26a69a",
      wickUpColor: "#ef5350",
      wickDownColor: "#26a69a",
    });

    candleSeries.setData(
      data.data.map((d) => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    const ma5Series = chart.addSeries(LineSeries, {
      color: "#2196F3",
      lineWidth: 2,
      title: "MA5",
    });

    // Filter out null MA values before passing to setData
    ma5Series.setData(
      data.data
        .map((d, i) => ({
          time: d.date,
          value: data.ma5[i],
        }))
        .filter((p): p is { time: string; value: number } => p.value !== null)
    );

    const ma20Series = chart.addSeries(LineSeries, {
      color: "#FF9800",
      lineWidth: 2,
      title: "MA20",
    });

    // Filter out null MA values before passing to setData
    ma20Series.setData(
      data.data
        .map((d, i) => ({
          time: d.date,
          value: data.ma20[i],
        }))
        .filter((p): p is { time: string; value: number } => p.value !== null)
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full" />;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/StockChart.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: stock chart with candlestick + MA5/MA20 overlay and null filtering"
```

### Task 4.4: AIAnalysis Component + Main Page

- [ ] **Step 1: Create `frontend/src/components/AIAnalysis.tsx`**

```tsx
interface AIAnalysisProps {
  analysis: string | null;
  loading: boolean;
}

export default function AIAnalysis({ analysis, loading }: AIAnalysisProps) {
  if (loading) {
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded border animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="mt-4 p-4 bg-gray-50 rounded border">
      <h3 className="font-bold text-lg mb-2">AI 趨勢分析</h3>
      <p className="text-gray-700 leading-relaxed">{analysis}</p>
      <p className="text-xs text-gray-400 mt-2">* 此分析僅描述趨勢，不構成投資建議</p>
    </div>
  );
}
```

- [ ] **Step 2: Update `frontend/src/app/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import StockInput from "@/components/StockInput";
import StockChart from "@/components/StockChart";
import AIAnalysis from "@/components/AIAnalysis";
import { fetchStock } from "@/services/stockApi";
import { StockResponse } from "@/types/stock";

export default function Home() {
  const [data, setData] = useState<StockResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (symbol: string) => {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await fetchStock(symbol);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "查詢失敗");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">台股技術分析</h1>
      <StockInput onSearch={handleSearch} loading={loading} error={error} />
      {data && (
        <div className="mt-6">
          <h2 className="text-xl font-semibold mb-2">
            {data.name ? `${data.symbol} ${data.name}` : data.symbol} 近 30 個交易日
          </h2>
          <StockChart data={data} />
          <AIAnalysis analysis={data.ai_analysis} loading={loading} />
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 3: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: AI analysis component and main page assembly"
```

---

## Module 5: Integration Agent

**職責:** Stock Router 組裝所有模組、更新 main.py、端對端驗證

**依賴:** Module 2 + 3 + 4 全部完成

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/stock.py`
- Create: `backend/tests/test_stock_router.py`
- Modify: `backend/app/main.py`

### Task 5.1: Stock Router

- [ ] **Step 1: Write test `backend/tests/test_stock_router.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.datasources.models import StockDailyData


def _make_data(n: int) -> list[StockDailyData]:
    return [
        StockDailyData(
            date=f"2026-03-{i+1:02d}",
            open=100.0+i, high=105.0+i, low=95.0+i,
            close=102.0+i, volume=1000*(i+1),
        )
        for i in range(n)
    ]


@pytest.fixture
def client():
    with patch("app.main.run_migrations", new_callable=AsyncMock), \
         patch("app.main.close_pool", new_callable=AsyncMock):
        from app.main import app
        with TestClient(app) as c:
            yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_stock_returns_30_days_with_full_ma(client):
    with patch("app.routers.stock.get_data_source") as mock_ds, \
         patch("app.routers.stock.get_ai_analyzer") as mock_ai, \
         patch("app.routers.stock.get_stock_name", new_callable=AsyncMock, return_value="台積電"):
        mock_ds.return_value = AsyncMock(get_daily_data=AsyncMock(return_value=_make_data(49)))
        mock_ai.return_value = AsyncMock(analyze=AsyncMock(return_value="趨勢分析"))

        resp = client.get("/api/stock/2330")

    body = resp.json()
    assert resp.status_code == 200
    assert body["symbol"] == "2330"
    assert body["name"] == "台積電"
    assert len(body["data"]) == 30
    assert len(body["ma5"]) == 30
    assert len(body["ma20"]) == 30
    assert all(v is not None for v in body["ma5"])
    assert all(v is not None for v in body["ma20"])
    assert body["ai_analysis"] == "趨勢分析"


def test_stock_graceful_without_ai(client):
    with patch("app.routers.stock.get_data_source") as mock_ds, \
         patch("app.routers.stock.get_ai_analyzer") as mock_ai, \
         patch("app.routers.stock.get_stock_name", new_callable=AsyncMock, return_value=None):
        mock_ds.return_value = AsyncMock(get_daily_data=AsyncMock(return_value=_make_data(49)))
        mock_ai.return_value = AsyncMock(analyze=AsyncMock(return_value=None))

        resp = client.get("/api/stock/2330")

    body = resp.json()
    assert resp.status_code == 200
    assert body["ai_analysis"] is None


def test_invalid_symbol_rejected(client):
    resp = client.get("/api/stock/AAPL")
    assert resp.status_code == 400
    assert "Invalid Taiwan stock symbol" in resp.json()["detail"]


def test_invalid_symbol_too_short(client):
    resp = client.get("/api/stock/12")
    assert resp.status_code == 400


def test_invalid_symbol_too_long(client):
    resp = client.get("/api/stock/1234567")
    assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_stock_router.py -v
```

Expected: FAIL

- [ ] **Step 3: Create `backend/app/routers/__init__.py`**

Empty file.

- [ ] **Step 4: Implement `backend/app/routers/stock.py`**

```python
import time

from fastapi import APIRouter, HTTPException

from app.datasources.interface import StockDataSource
from app.datasources.yfinance_source import YFinanceSource
from app.datasources.twse_source import TWSESource
from app.datasources.fallback_source import FallbackDataSource
from app.datasources.db_source import DatabaseDataSource
from app.datasources.cached_source import CachedDataSource
from app.services.indicator import IndicatorService
from app.services.ai_analyzer import AIAnalyzer, OpenAIAnalyzer
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
        _ai_analyzer = OpenAIAnalyzer()
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
    # Validate Taiwan stock symbol: digits only, 3-6 characters
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
        ai_result = await analyzer.analyze(symbol, display_data, display_ma5, display_ma20)
        ttl = get_ttl_seconds()
        _ai_cache[symbol] = (ai_result, now + ttl)

    # Fetch stock name (cached inside YFinanceSource)
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
```

- [ ] **Step 5: Update `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.connection import close_pool
from app.db.migrations import run_migrations
from app.routers.stock import router as stock_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    yield
    await close_pool()


app = FastAPI(title="TW Stock Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Run router tests**

```bash
cd backend && python -m pytest tests/test_stock_router.py -v
```

Expected: All PASS

- [ ] **Step 7: Run ALL backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/ backend/app/main.py backend/tests/test_stock_router.py
git commit -m "feat: stock API router with validation, AI cache, and name lookup"
```

### Task 5.2: End-to-End Verification

- [ ] **Step 1: Create `.env`**

```bash
cp .env.example .env
# Edit .env: add real OPENAI_API_KEY
```

- [ ] **Step 2: Start all containers**

```bash
docker-compose up --build
```

Expected: All 3 containers start without errors.

- [ ] **Step 3: Verify health**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Verify stock API**

```bash
curl http://localhost:8000/api/stock/2330
```

Expected: JSON with `symbol`, `name`, 30 items in `data`, 30 non-null `ma5`, 30 non-null `ma20`, `ai_analysis`.

- [ ] **Step 5: Verify invalid symbol rejection**

```bash
curl http://localhost:8000/api/stock/AAPL
```

Expected: `{"detail":"Invalid Taiwan stock symbol"}` with HTTP 400.

- [ ] **Step 6: Verify frontend**

Open `http://localhost:3000`. Enter "2330", click search. Verify:
- Candlestick chart renders with red up / green down
- MA5 blue line visible
- MA20 orange line visible
- AI analysis text appears below
- Stock name appears in the heading

- [ ] **Step 7: Verify DB persistence**

```bash
docker-compose exec db psql -U postgres -d stockdb -c "SELECT COUNT(*) FROM stock_daily_data WHERE symbol='2330';"
```

Expected: Count >= 49

- [ ] **Step 8: Verify cache (query same stock twice)**

Second query for "2330" should return instantly (< 50ms vs first query > 1s).

- [ ] **Step 9: Final commit**

```bash
git add -A
git commit -m "feat: Taiwan stock technical analyzer - complete"
```
