# Taiwan Stock Technical Analyzer - Design Spec

## Overview

Web system that accepts a Taiwan stock symbol, retrieves the last 30 trading days of data, calculates MA5/MA20, displays a price chart with MA curves, and generates AI trend analysis in Traditional Chinese (no investment advice).

**Data fetch strategy:** To ensure MA20 has values from day 1 of the displayed range, the backend fetches 49 trading days (30 display + 19 lookback) from the data source, calculates MA over the full range, then returns only the last 30 days of OHLCV and MA values to the frontend. All 30 MA5 and MA20 values are non-null.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (React) + TradingView Lightweight Charts |
| Backend | Python FastAPI (async) |
| AI Analysis | OpenAI API |
| Data Source | yfinance (primary), TWSE (fallback) |
| Database | PostgreSQL (persistent storage for HA) |
| Infrastructure | Docker Compose (full containerized) |

## Architecture

```
┌─────────────────────────────────────────┐
│  Next.js (React + TradingView LWC)      │  UI Layer
│  ├─ Stock symbol input                  │
│  ├─ Price chart + MA5/MA20 curves       │
│  └─ AI trend analysis text              │
└──────────────────┬──────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────┐
│  FastAPI (async)                        │  Service Layer
│                                         │
│  ├─ GET /api/stock/{symbol}             │
│  │   → OHLCV + MA5/MA20 + AI analysis  │
│  │                                      │
│  ├─ GET /health                         │
│  │                                      │
│  ├─ CachedDataSource (in-memory)        │  Smart TTL + Dedup
│  │   └─ DatabaseDataSource (PostgreSQL) │  Persistent storage
│  │       └─ FallbackDataSource          │  Auto failover
│  │           ├─ YFinanceSource (primary)│
│  │           └─ TWSESource (fallback)   │
│  │                                      │
│  ├─ IndicatorService                    │  Pure calc: MA5/MA20
│  │                                      │
│  └─ AIAnalyzer (interface)              │  Graceful degradation
│      └─ OpenAIAnalyzer (impl)           │
└─────────────────────────────────────────┘
```

## Design Principles

1. **Interface-driven**: UI layer and DataSource layer separated by abstractions. Swap data sources or AI providers by adding implementations, not changing architecture.
2. **Decorator pattern for cross-cutting concerns**: Cache and fallback are decorators wrapping the base DataSource, not baked into each implementation.
3. **Graceful degradation**: If AI analysis fails, still return chart data. Partial availability > total failure.
4. **No over-engineering**: Build exactly what the requirements ask for. Clean layering naturally supports future extensions without pre-built abstractions.

## Backend Modules

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, /health
│   ├── config.py               # Settings (OpenAI key, cache config)
│   ├── routers/
│   │   └── stock.py            # GET /api/stock/{symbol}
│   ├── datasources/
│   │   ├── interface.py        # StockDataSource ABC
│   │   ├── models.py           # StockDailyData dataclass
│   │   ├── yfinance_source.py  # Primary: yfinance ({symbol}.TW)
│   │   ├── twse_source.py      # Fallback: TWSE Open API
│   │   ├── db_source.py        # PostgreSQL persistent storage
│   │   ├── cached_source.py    # In-memory TTL cache + fetch dedup
│   │   └── fallback_source.py  # Auto-failover decorator
│   ├── db/
│   │   ├── connection.py       # AsyncPG connection pool
│   │   └── migrations.py       # Schema initialization
│   ├── services/
│   │   ├── indicator.py        # Calculate MA5, MA20
│   │   └── ai_analyzer.py      # OpenAI trend analysis
│   └── utils/
│       ├── trading_calendar.py # TW stock trading calendar
│       └── cache_ttl.py        # Smart TTL calculation
├── holidays/
│   └── 2026.json               # TWSE holiday schedule
├── Dockerfile
└── requirements.txt
```

### DataSource Interface

```python
class StockDataSource(ABC):
    @abstractmethod
    async def get_daily_data(self, symbol: str, days: int) -> list[StockDailyData]

@dataclass
class StockDailyData:
    date: str       # YYYY-MM-DD
    open: float     # Opening price
    high: float     # High price
    low: float      # Low price
    close: float    # Closing price
    volume: int     # Volume
```

### DataSource Composition

```
CachedDataSource (in-memory TTL + dedup)
  └─ DatabaseDataSource (PostgreSQL persistent storage)
      └─ FallbackDataSource (try primary, fallback on error)
          ├─ YFinanceSource
          └─ TWSESource
```

**Data flow:**
1. Check in-memory cache → hit: return
2. Check PostgreSQL → hit & fresh: return (write to memory cache)
3. Fetch from external API (yfinance → TWSE fallback) → write to DB + memory cache → return
4. All external APIs down → return stale data from DB (with data timestamp)

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

### Cache Strategy

**Smart TTL based on Taiwan stock trading calendar:**

| Query Time | TTL Target | Example |
|-----------|-----------|---------|
| During trading (09:00-13:30) | Until 13:30 same day | Mon 10:00 → cache until Mon 13:30 (data is up to previous close; refresh at 13:30 to pick up today's close) |
| After close (13:30+) | Until next trading day 09:00 | Mon 14:00 → cache until Tue 09:00 |
| Weekend/Holiday | Until next trading day 09:00 | Fri 14:00 → cache until Mon 09:00 |

**Trading Calendar (`trading_calendar.py`):**
- Base rules: Sat/Sun closed
- Holidays: Loaded from JSON config (updated annually from TWSE announcements)
- Core function: `get_next_trading_day_open(now) -> datetime`

**Fetch Deduplication:**
- Concurrent requests for the same symbol share a single API call
- Implementation: `asyncio.Lock` per cache key (referenced from iOS `DtNoCacheManager.isFetchingDict` pattern)

### Indicator Service

```python
class IndicatorService:
    @staticmethod
    def calculate_ma(prices: list[float], period: int) -> list[float | None]:
        """Simple moving average. Returns None for insufficient data points."""
```

Pure calculation, no state, no I/O.

### AI Analyzer

```python
class AIAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, symbol: str, data: list[StockDailyData], ma5: list, ma20: list) -> str

class OpenAIAnalyzer(AIAnalyzer):
    """Send actual price data + MA values to OpenAI, get trend description in Traditional Chinese.

    Prompt constraints:
    - Must describe trends based on actual data
    - Must NOT provide investment advice
    - Response in Traditional Chinese
    """
```

Graceful degradation: if OpenAI call fails, API returns data without `ai_analysis` field (not an error).

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
      "volume": 35000
    }
  ],
  "ma5": [891.2, 889.8, 890.5, "...30 values, all non-null"],
  "ma20": [888.5, 889.1, 890.0, "...30 values, all non-null"],
  "ai_analysis": "近 30 個交易日中，2330 股價呈現..."
}
```

## Frontend Modules

```
frontend/
├── src/
│   ├── app/
│   │   └── page.tsx            # Main page
│   ├── components/
│   │   ├── StockInput.tsx      # Symbol input + search button
│   │   ├── StockChart.tsx      # TradingView LWC: price line + MA5/MA20
│   │   └── AIAnalysis.tsx      # AI analysis text display
│   ├── services/
│   │   └── stockApi.ts         # Fetch from backend API
│   └── types/
│       └── stock.ts            # TypeScript type definitions
├── Dockerfile
├── package.json
└── next.config.js
```

### Components

**StockInput:** Text input for stock symbol (e.g., "2330"), search button, loading state, error display.

**StockChart:** TradingView Lightweight Charts with:
- Candlestick or line series for price data
- Two line series overlaid for MA5 (short-term) and MA20 (long-term)
- Color-coded: MA5 blue, MA20 orange
- Responsive sizing

**AIAnalysis:** Renders the `ai_analysis` text from API response. Shows placeholder if AI analysis is unavailable (graceful degradation).

## Docker Compose

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/stockdb
    depends_on:
      - db

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

volumes:
  pgdata:
```

Three containers, `docker-compose up` to start.

## Future Data Sources (Not In Scope)

| Source | Status | Blocker |
|--------|--------|---------|
| DTNO (CMoney internal API) | Future | Need JWT token acquisition mechanism. [DTNO 資料源申請文件](https://docs.google.com/document/d/13yS1jZ6Bu6b134MyAX3ClKOsw01xXKhFDJNpid8rZUU/edit?tab=t.0#heading=h.tkmvzuafrrdq) |
| FinMind | Available | Lower priority than TWSE for fallback |

When DTNO becomes available, add `DtnoSource` implementing `StockDataSource` with JWT token management encapsulated within the implementation. No architecture changes needed.

## Internal Project References

| Reference | What We Borrowed |
|-----------|-----------------|
| `llm-stock-team-analyzer` (`dataflows/interface.py`) | DataSource abstraction pattern, yfinance error handling |
| `llm-stock-team-analyzer` (`dataflows/indicators.py`) | MA calculation reference |
| iOS `DtNoCacheManager` | TTL cache + fetch dedup pattern |
| Android `CoroutineBaseRepository` | Template method: cache → API → store pattern |
| iOS `GetTWStockDayKLineDataRepositoryImpl` | DTNO API format reference (for future) |
| Android `DomainAdapter` | Environment-based URL switching pattern |

## Non-Goals

- Real-time / intraday data
- Multiple stock comparison
- Watchlist / favorites
- User authentication
- Technical indicators beyond MA5/MA20
- Investment advice or recommendations
