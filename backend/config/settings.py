import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App Settings
    ENV: str = os.getenv("ENV", "development")
    SERVER_URL: str = os.getenv("SERVER_URL", "http://localhost:8000")
    # Comma-separated list of browser origins allowed by CORS (the dashboard).
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173")
    # Public URL of the dashboard, used to build password-reset / invite links.
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:3000")
    
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

    # Email (SMTP) for password reset + team invites. If SMTP_HOST is empty,
    # links are logged server-side instead of emailed (dev mode).
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587") or "587")
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"
    
    # MiniMax Configuration (LLM + TTS). Base URL is configurable per account/
    # region: international = https://api.minimax.io/v1 (default); mainland-China
    # accounts use a different host. The LLM endpoint is OpenAI-compatible.
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_GROUP_ID: str = os.getenv("MINIMAX_GROUP_ID", "")
    MINIMAX_API_BASE: str = os.getenv("MINIMAX_API_BASE", "https://api.minimax.io/v1")
    MINIMAX_LLM_MODEL: str = os.getenv("MINIMAX_LLM_MODEL", "MiniMax-M3")
    MINIMAX_TTS_MODEL: str = os.getenv("MINIMAX_TTS_MODEL", "speech-02-turbo")
    MINIMAX_TTS_VOICE: str = os.getenv("MINIMAX_TTS_VOICE", "male-qn-qingse")
    # MiniMax TTS language hint for correct pronunciation (e.g. "Hindi", "English", "auto").
    MINIMAX_LANGUAGE_BOOST: str = os.getenv("MINIMAX_LANGUAGE_BOOST", "Hindi")

    # Speech-to-Text (ASR) via Deepgram. MiniMax does NOT offer STT.
    # Get a key at https://console.deepgram.com/. STT stays in mock mode while
    # DEEPGRAM_API_KEY is empty. nova-3 is Deepgram's current general model and
    # handles 8kHz phone audio well.
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    DEEPGRAM_URL: str = os.getenv("DEEPGRAM_URL", "https://api.deepgram.com/v1/listen")
    # nova-2 supports Hindi (and 36+ languages); callers here speak Hindi.
    DEEPGRAM_MODEL: str = os.getenv("DEEPGRAM_MODEL", "nova-2")
    DEEPGRAM_LANGUAGE: str = os.getenv("DEEPGRAM_LANGUAGE", "hi")
    
    # Vobiz (Indian Calling) Configuration
    VOBIZ_SIP_DOMAIN: str = os.getenv("VOBIZ_SIP_DOMAIN", "")
    VOBIZ_USERNAME: str = os.getenv("VOBIZ_USERNAME", "")
    VOBIZ_PASSWORD: str = os.getenv("VOBIZ_PASSWORD", "")
    VOBIZ_OUTBOUND_NUMBER: str = os.getenv("VOBIZ_OUTBOUND_NUMBER", "")
    DEFAULT_TRANSFER_NUMBER: str = os.getenv("DEFAULT_TRANSFER_NUMBER", "")
    SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", "You are a warm, professional AI receptionist answering inbound phone calls for a clinic. Your primary goal is to book appointments for callers. Greet the caller, answer brief questions, and collect what you need to book: the caller's full name, preferred date, preferred time, and reason for the visit. As soon as you have a date and time, call the book_appointment tool to confirm, then read the confirmation back. Use lookup_caller to recognise returning patients. If the caller asks for a human or describes an emergency, use transfer_call. Always speak with the caller in Hindi. Keep every reply short, natural, and under two sentences.")
    INITIAL_GREETING: str = os.getenv("INITIAL_GREETING", "Greet the caller warmly, introduce yourself as the clinic's AI receptionist, and ask how you can help them book an appointment today.")

settings = Settings()
