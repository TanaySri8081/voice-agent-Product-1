import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    ENV: str = os.getenv("ENV", "development")
    SERVER_URL: str = os.getenv("SERVER_URL", "http://localhost:8000")
    
    # Database Settings (Supabase Postgres)
    # Two ways to configure it (DATABASE_URL wins if it is set):
    #   1. DATABASE_URL = full postgresql:// URI (driver is normalised in db.py).
    #   2. The DB_* parts below. Preferred when the password contains special
    #      characters (@, #, :, /) because NO URL-encoding is needed here.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: int = int(os.getenv("DB_PORT", "6543") or "6543")
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Auth Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-receptionist-key-change-this-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # MiniMax Configuration (LLM + TTS). Base URL is configurable per account/
    # region: international = https://api.minimax.io/v1 (default); mainland-China
    # accounts use a different host. The LLM endpoint is OpenAI-compatible.
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_GROUP_ID: str = os.getenv("MINIMAX_GROUP_ID", "")
    MINIMAX_API_BASE: str = os.getenv("MINIMAX_API_BASE", "https://api.minimax.io/v1")
    MINIMAX_LLM_MODEL: str = os.getenv("MINIMAX_LLM_MODEL", "abab6.5g-chat")
    MINIMAX_TTS_MODEL: str = os.getenv("MINIMAX_TTS_MODEL", "speech-02-turbo")
    MINIMAX_TTS_VOICE: str = os.getenv("MINIMAX_TTS_VOICE", "male-qn-qingse")

    # Speech-to-Text (ASR). MiniMax does NOT offer STT, so this points at a
    # separate OpenAI-compatible transcription API (e.g. OpenAI Whisper). STT
    # stays in mock mode while STT_API_KEY is empty.
    STT_API_BASE: str = os.getenv("STT_API_BASE", "https://api.openai.com/v1")
    STT_API_KEY: str = os.getenv("STT_API_KEY", "")
    STT_MODEL: str = os.getenv("STT_MODEL", "whisper-1")
    
    # Vobiz (Indian Calling) Configuration
    VOBIZ_SIP_DOMAIN: str = os.getenv("VOBIZ_SIP_DOMAIN", "")
    VOBIZ_USERNAME: str = os.getenv("VOBIZ_USERNAME", "")
    VOBIZ_PASSWORD: str = os.getenv("VOBIZ_PASSWORD", "")
    VOBIZ_OUTBOUND_NUMBER: str = os.getenv("VOBIZ_OUTBOUND_NUMBER", "")
    DEFAULT_TRANSFER_NUMBER: str = os.getenv("DEFAULT_TRANSFER_NUMBER", "")
    SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", "You are a helpful, professional, and empathetic AI receptionist for a medical clinic. You help patients lookup their details, schedule appointments, and answer questions. Keep your answers concise, friendly, and under two sentences.")
    INITIAL_GREETING: str = os.getenv("INITIAL_GREETING", "Hello! Thank you for calling the clinic. I am your AI receptionist. How can I help you today?")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
