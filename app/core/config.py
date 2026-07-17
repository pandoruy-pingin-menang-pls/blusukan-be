from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_ANON_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    GEMINI_API_KEY: str
    GEMINI_MODEL_TEXT: str = "gemini-2.5-flash"
    GEMINI_MODEL_VISION: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    REDIS_URL: str
    CELERY_BROKER_URL: str
    WEATHER_API_KEY: str
    OSRM_BASE_URL: str = "http://localhost:5000"
    SUPABASE_STORAGE_BUCKET_MENU: str = "merchant-menus"
    SUPABASE_STORAGE_BUCKET_VOICE: str = "merchant-voicenotes"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    class Config:
        env_file = ".env"

settings = Settings()
