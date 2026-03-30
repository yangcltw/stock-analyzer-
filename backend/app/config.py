from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/stockdb"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    cache_ttl_default: int = 3600
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
