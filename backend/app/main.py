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
