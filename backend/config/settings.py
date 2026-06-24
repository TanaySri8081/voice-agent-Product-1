import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    ENV: str = os.getenv("ENV", "development")
    SERVER_URL: str = os.getenv("SERVER_URL", "http://localhost:8000")
    
    # Database Settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "ai_receptionist")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Auth Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-receptionist-key-change-this-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # MiniMax Configuration
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_GROUP_ID: str = os.getenv("MINIMAX_GROUP_ID", "")
    MINIMAX_LLM_MODEL: str = os.getenv("MINIMAX_LLM_MODEL", "abab6.5g-chat")
    MINIMAX_TTS_MODEL: str = os.getenv("MINIMAX_TTS_MODEL", "speech-01-turbo")
    MINIMAX_TTS_VOICE: str = os.getenv("MINIMAX_TTS_VOICE", "male-qn-qingse")
    
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
