# Taiwan Stock Technical Analyzer - Design Spec

## Overview

Web system that accepts a Taiwan stock symbol, retrieves the last 30 trading days of data, calculates MA5/MA20, displays a price chart with MA curves, and generates AI trend analysis in Traditional Chinese (no investment advice).

**Data fetch strategy:** To ensure MA20 has values from day 1 of the displayed range, the backend fetches 49 trading days (30 display + 19 lookback) from the data source, calculates MA over the full range, then returns only the last 30 days of OHLCV and MA values to the frontend. All 30 MA5 and MA20 values are non-null.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (React) + TradingView Lightweight Charts |
| Backend | Python FastAPI (async) |
| AI Analysis | Gemini 2.5 Flash (primary), OpenAI GPT-4o-mini (fallback) |
| Data Source | yfinance (primary), TWSE Open API (fallback) |
| Database | PostgreSQL (persistent storage for HA) |
| Infrastructure | Docker Compose (full containerized, multi-stage frontend build) |

## Architecture

```
┌─────────────────────────────────────────┐
│  Next.js (React + TradingView LWC)      │  UI Layer
│  ├─ Sticky header + search bar          │
│  ├─ Candlestick chart + MA5/MA20        │  Full-screen RWD
│  ├─ AI trend analysis text              │
│  └─ Collapsible data table + MA columns │
└──────────────────┬──────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────┐
│  FastAPI (async)                        │  Service Layer
│                                         │
│  ├─ GET /api/stock/{symbol}             │
│  │   → OHLCV + MA5/MA20 + AI analysis  │
│  │   → Symbol validation (digits, 3-6) │
│  │                                      │
│  ├─ GET /health                         │
│  │                                      │
│  ├─ CachedDataSource (in-memory)        │  Smart TTL + Dedup
│  │   └─ DatabaseDataSource (PostgreSQL) │  Fresh/stale split
│  │       └─ FallbackDataSource          │  Auto failover
│  │           ├─ YFinanceSource (primary)│
│  │           └─ TWSESource (fallback)   │
│  │                                      │
│  ├─ IndicatorService                    │  Pure calc: MA5/MA20
│  │                                      │
│  └─ FallbackAIAnalyzer                  │  Graceful degradation
│      ├─ GeminiAnalyzer (primary)        │
│      └─ OpenAIAnalyzer (fallback)       │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  PostgreSQL                             │  Data Layer
│  └─ stock_daily_data table              │
└─────────────────────────────────────────┘
```

**Data flow:**
1. Check in-memory cache → hit & not expired: return
2. Check PostgreSQL → hit & fresh (within `freshness_hours`): return (write to memory cache)
3. Fetch from external API (yfinance → TWSE fallback) → write to DB + memory cache → return
4. All external APIs down → return stale data from DB (no freshness filter, last resort)

## Design Principles

1. **Interface-driven**: UI layer and DataSource layer separated by abstractions. Swap data sources or AI providers by adding implementations, not changing architecture.
2. **Decorator pattern for cross-cutting concerns**: Cache, fallback, and DB persistence are decorators wrapping the base DataSource, not baked into each implementation.
3. **Graceful degradation**: If AI analysis fails, still return chart data. If primary data source fails, fallback to secondary. If all external APIs fail, serve stale DB data. Partial availability > total failure.
4. **Fallback at every layer**: Data sources (yfinance → TWSE), AI analyzers (Gemini → OpenAI), DB (fresh → stale).
5. **Only cache success**: Failed AI results are NOT cached, so the next request retries immediately.

## Backend Modules

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS (env-driven), /health, lifespan
│   ├── config.py               # Settings (Gemini key, OpenAI key, CORS origins, DB URL)
│   ├── routers/
│   │   └── stock.py            # GET /api/stock/{symbol} with symbol validation + AI cache
│   ├── datasources/
│   │   ├── interface.py        # StockDataSource ABC (count: int param)
│   │   ├── models.py           # StockDailyData dataclass
│   │   ├── yfinance_source.py  # Primary: yfinance ({symbol}.TW) + get_stock_name()
│   │   ├── twse_source.py      # Fallback: TWSE Open API (ROC date conversion)
│   │   ├── db_source.py        # PostgreSQL with fresh/stale read split
│   │   ├── cached_source.py    # In-memory TTL cache + fetch dedup (setdefault lock)
│   │   └── fallback_source.py  # Auto-failover decorator
│   ├── db/
│   │   ├── connection.py       # AsyncPG connection pool
│   │   └── migrations.py       # Schema initialization
│   ├── services/
│   │   ├── indicator.py        # Calculate MA5, MA20
│   │   └── ai_analyzer.py      # GeminiAnalyzer, OpenAIAnalyzer, FallbackAIAnalyzer
│   └── utils/
│       ├── trading_calendar.py # TW stock trading calendar + missing-year warning
│       └── cache_ttl.py        # Smart TTL calculation (market hours aware)
├── holidays/
│   └── 2026.json               # TWSE holiday schedule
├── tests/                      # 73 unit tests
├── Dockerfile
└── requirements.txt
```

### DataSource Interface

```python
class StockDataSource(ABC):
    @abstractmethod
    async def get_daily_data(self, symbol: str, count: int) -> list[StockDailyData]:
        """Fetch daily stock data.

        Args:
            symbol: Taiwan stock symbol (digits only, e.g. "2330").
            count: Number of trading day rows to return.
        """

@dataclass
class StockDailyData:
    date: str       # YYYY-MM-DD
    open: float     # Opening price
    high: float     # High price
    low: float      # Low price
    close: float    # Closing price
    volume: int     # Volume (shares)
```

### DataSource Composition

```
CachedDataSource (in-memory TTL + dedup via asyncio.Lock setdefault)
  └─ DatabaseDataSource (PostgreSQL, fresh/stale split, freshness_hours=24)
      └─ FallbackDataSource (try primary, fallback on error)
          ├─ YFinanceSource ({symbol}.TW, run_in_executor for sync yfinance)
          └─ TWSESource (TWSE STOCK_DAY API, ROC date → ISO conversion)
```

### Database Schema

```sql
CREATE TABLE stock_daily_data (
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
);

CREATE INDEX idx_stock_daily_symbol_date ON stock_daily_data(symbol, date DESC);
```

### DatabaseDataSource — Fresh/Stale Split

- **`_read_fresh_from_db`**: Queries with `fetched_at > NOW() - INTERVAL '1 hour' * freshness_hours`. Used on the happy path.
- **`_read_stale_from_db`**: No freshness filter. Used only when all upstream APIs fail — returns whatever the DB has as a last resort.
- **`_write_to_db`**: UPSERT with `ON CONFLICT ... DO UPDATE`. Wrapped in try/except so write failure doesn't block data return.
- Date strings are converted to `datetime.date` objects before writing to asyncpg.

### Cache Strategy

**Smart TTL based on Taiwan stock trading calendar:**

| Query Time | TTL Target | Example |
|-----------|-----------|---------|
| Before/during trading (< 13:30) | Until 13:30 same day | Mon 08:00 → cache until Mon 13:30 |
| After close (13:30+) | Until next trading day 09:00 | Mon 14:00 → cache until Tue 09:00 |
| Weekend/Holiday | Until next trading day 09:00 | Fri 14:00 → cache until Mon 09:00 |

**Trading Calendar (`trading_calendar.py`):**
- Base rules: Sat/Sun closed
- Holidays: Loaded from JSON config (updated annually from TWSE announcements)
- Startup warning if no holidays for current year
- Core function: `get_next_trading_day_open(now) -> datetime`

**Fetch Deduplication:**
- Concurrent requests for the same symbol share a single API call
- Implementation: `self._locks.setdefault(cache_key, asyncio.Lock())` — atomic in CPython

### Indicator Service

```python
class IndicatorService:
    @staticmethod
    def calculate_ma(prices: list[float], period: int) -> list[float | None]:
        """Simple moving average. Returns None for insufficient data points."""
```

Pure calculation, no state, no I/O.

### AI Analyzer — Fallback Chain

```python
class AIAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, symbol, data, ma5, ma20) -> str | None: ...

class GeminiAnalyzer(AIAnalyzer):
    """Primary. Uses Gemini 2.5 Flash with thinking disabled."""

class OpenAIAnalyzer(AIAnalyzer):
    """Fallback. Uses GPT-4o-mini."""

class FallbackAIAnalyzer(AIAnalyzer):
    """Tries primary, falls back to secondary on None result."""
```

**System prompt:**
```
你是一位台股技術分析助手。請根據提供的實際股價數據和均線數據，用繁體中文描述股價趨勢。你必須：
1. 只根據實際數據描述趨勢
2. 絕對不可以提供任何投資建議
3. 不可以建議買入、賣出或持有
4. 回覆限制在 200 字以內
```

**AI Cache policy:** Successful results cached with same smart TTL. Failed results (None) are NOT cached — next request retries immediately.

### Symbol Validation

```python
if not symbol.isdigit() or not (3 <= len(symbol) <= 6):
    raise HTTPException(status_code=400, detail="Invalid Taiwan stock symbol")
```

### API Response Format

```json
{
  "symbol": "2330",
  "name": "台積電",
  "data": [
    {
      "date": "2026-03-02",
      "open": 890.0,
      "high": 895.0,
      "low": 885.0,
      "close": 892.0,
      "volume": 35185922
    }
  ],
  "ma5": [891.2, 889.8, 890.5, "...30 values, all non-null"],
  "ma20": [888.5, 889.1, 890.0, "...30 values, all non-null"],
  "ai_analysis": "近 30 個交易日中，2330 股價呈現..."
}
```

`name` is fetched from yfinance `ticker.info["longName"]` with internal cache. Returns `null` if lookup fails.

## Frontend Modules

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout (forced light theme, lang=zh-TW)
│   │   ├── page.tsx            # Main page (full-screen RWD)
│   │   └── globals.css         # Forced light theme (no dark mode)
│   ├── components/
│   │   ├── StockInput.tsx      # Symbol input + search button (responsive)
│   │   ├── StockChart.tsx      # TradingView LWC: candlestick + MA5/MA20 + legend
│   │   └── AIAnalysis.tsx      # AI analysis card with disclaimer
│   ├── services/
│   │   └── stockApi.ts         # Fetch from backend API
│   └── types/
│       └── stock.ts            # TypeScript types (ma5/ma20 as (number|null)[])
├── Dockerfile                  # Multi-stage build (builder + standalone runner)
├── package.json
├── next.config.ts              # output: "standalone"
└── tsconfig.json
```

### Frontend Layout (RWD)

**Desktop (>= 640px):**
- Sticky header: title left, search right
- Chart height: 500px
- Data table shows all columns including volume

**Mobile (< 640px):**
- Header: title top, search below
- Chart height: 300px, smaller font
- Data table hides volume column

### Page Structure

1. **Sticky Header** — Title + search input
2. **Stock Info Bar** — Symbol, name, latest close, MA5, MA20 values
3. **Chart Card** — Candlestick + MA5 (blue) / MA20 (orange) + legend
4. **AI Analysis Card** — Trend description + disclaimer
5. **Collapsible Data Table** — 30 rows with date, OHLCV, MA5, MA20 columns, red/green coloring

### Chart Details

- **Up candles**: Red (#ef5350) — Taiwan convention
- **Down candles**: Green (#26a69a) — Taiwan convention
- **MA5 line**: Blue (#2196F3)
- **MA20 line**: Orange (#FF9800)
- **Null MA filtering**: `.filter((p) => p.value !== null)` before `setData`
- **Responsive resize**: `window.addEventListener("resize", ...)` updates chart width/height

### Forced Light Theme

Dark mode is disabled. `globals.css` does not include `prefers-color-scheme: dark`. Background is `#f9fafb`, text is `#111827`.

## Docker Compose

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

**Frontend Dockerfile:** Multi-stage build. Builder stage runs `npm run build` with `NEXT_PUBLIC_API_URL` as build arg. Runner stage uses Next.js standalone output (`node server.js`).

**CORS:** Driven by `CORS_ORIGINS` environment variable (comma-separated), not hardcoded.

Three containers, `docker-compose up --build` to start.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes (for AI) | Google Gemini API key |
| `OPENAI_API_KEY` | No | OpenAI API key (fallback) |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default: `http://localhost:3000`) |

## TWSE API Column Mapping

Real TWSE STOCK_DAY column order:
```
[0] 日期, [1] 成交股數, [2] 成交金額, [3] 開盤價, [4] 最高價,
[5] 最低價, [6] 收盤價, [7] 漲跌價差, [8] 成交筆數
```

Note: 成交股數 ([1]) is in shares (not lots). Date is in ROC format (e.g., "115/03/02" = 2026-03-02).

## Non-Goals

- Real-time / intraday data
- Multiple stock comparison
- Watchlist / favorites
- User authentication
- Technical indicators beyond MA5/MA20
- Investment advice or recommendations
