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
