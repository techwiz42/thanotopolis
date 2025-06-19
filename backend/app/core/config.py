import os
import json
import logging
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from dotenv import load_dotenv

# Determine env file path
# DEV environment now lives on the swarmchat Digital Ocean droplet
env_path = '/home/peter/thanotopolis/backend/.env'
load_dotenv(env_path)

# Set up logger
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    model_config = ConfigDict(extra='ignore', env_file=env_path)
    
    # API Settings
    API_VERSION: str = "1.0"
    PROJECT_NAME: str = "Cyberiad"
    
    MAX_CONTEXT_MESSAGES: int = 25

    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    FRONTEND_URL: Optional[str] = os.getenv("FRONTEND_URL")

    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")  # Keep 0.0.0.0 for binding but...
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_URL: Optional[str] = os.getenv("API_URL")  # Add this for external URL

    # Testing
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_thanotopolis"
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Parse CORS origins from env or use default
    # Expecting comma-separated list in env var
    cors_origins_str: Optional[str] = os.getenv("CORS_ORIGINS")
    try:
        CORS_ORIGINS: List[str] = json.loads(cors_origins_str) if cors_origins_str else []
    except json.JSONDecodeError:
        logger.error("Invalid CORS_ORIGINS format in env.")
        raise

    # RAG settings
    BUFFER_SAVE_DIR: Optional[str] = os.getenv("BUFFER_SAVE_DIR")
    CHROMA_PERSIST_DIR: Optional[str] = os.getenv("CHROMA_PERSIST_DIR")
    RAG_CHUNK_SIZE: Optional[str] = os.getenv("RAG_CHUNK_SIZE")
    RAG_CHUNK_OVERLAP: Optional[str] = os.getenv("RAG_CHUNK_OVERLAP")

    WS_ORIGINS: List[str] = []
 
    # Redis has been removed from this application

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))  # seconds
    WS_CONNECTION_TIMEOUT: int = int(os.getenv("WS_CONNECTION_TIMEOUT", "3600"))  # 1 hour

    # Microsoft OneDrive Settings
    MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID", "NONE")
    MICROSOFT_CLIENT_SECRET: str = os.getenv("MICROSOFT_CLIENT_SECRET", "NONE")
    MICROSOFT_TENANT_ID: str = os.getenv("MICROSOFT_TENANT_ID", "NONE")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "NONE")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "NONE")
    GOOGLE_SEARCH_ENGINE_ID: str = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "NONE")

    # Stripe
    STRIPE_CUSTOMER_ID: Optional[str] = os.getenv("STRIPE_CUSTOMER_ID")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "sk_test_")  # Sandbox key placeholder
    STRIPE_PUBLIC_KEY: str = os.getenv("STRIPE_PUBLIC_KEY", "pk_test_")  # Sandbox key placeholder
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_")  # Webhook secret

    STRIPE_PROD_10K_TOKENS: Optional[str] = os.getenv("STRIPE_PROD_10K_TOKENS")
    STRIPE_PROD_50K_TOKENS: Optional[str] = os.getenv("STRIPE_PROD_50K_TOKENS")
    STRIPE_PROD_100K_TOKENS: Optional[str] = os.getenv("STRIPE_PROD_100K_TOKENS")
    STRIPE_PROD_BASIC_SUB: Optional[str] = os.getenv("STRIPE_PROD_BASIC_SUB")
    STRIPE_PROD_PRO_SUB: Optional[str] = os.getenv("STRIPE_PROD_PRO_SUB")

    STRIPE_PRICE_PRO_SUB: Optional[str] = os.getenv("STRIPE_PRICE_PRO_SUB")
    STRIPE_PRICE_BASIC_SUB: Optional[str] = os.getenv("STRIPE_PRICE_BASIC_SUB")
    STRIPE_PRICE_100K_TOKENS: Optional[str] = os.getenv("STRIPE_PRICE_100K_TOKENS")
    STRIPE_PRICE_50K_TOKENS: Optional[str] = os.getenv("STRIPE_PRICE_50K_TOKENS")
    STRIPE_PRICE_10K_TOKENS: Optional[str] = os.getenv("STRIPE_PRICE_10K_TOKENS")

    # Voice Settings
    DEEPGRAM_MODEL: str = os.getenv("DEEPGRAM_MODEL", "nova-2")  # Changed from nova-3 to nova-2 for better language support
    DEEPGRAM_LANGUAGE: str = os.getenv("DEEPGRAM_LANGUAGE", "en-US")
    ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "TxGEqnHWrfWFTfGW9XjX")  # James voice
    ELEVENLABS_OPTIMIZE_STREAMING_LATENCY: int = int(os.getenv("ELEVENLABS_OPTIMIZE_STREAMING_LATENCY", "3"))
    ELEVENLABS_OUTPUT_FORMAT: str = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")


    # Agent Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "YOU_GOT_NOTHIN")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "NOT_SET")
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "NOT_SET")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "NOT_SET")

    DEFAULT_AGENT_MODEL: str = "gpt-4o-mini"
    AGENT_RESPONSE_TIMEOUT: int = 120  # seconds
    MAX_TURNS: int = 50

    SMTP_FROM_EMAIL: str = "pete@cyberiad.ai"
    SMTP_FROM_NAME: str = "Cyberiad.ai"

settings = Settings()

# Compute WebSocket origins from CORS origins
for origin in settings.CORS_ORIGINS:
    if origin.startswith('http://'):
        settings.WS_ORIGINS.append(origin.replace('http://', 'ws://'))
    elif origin.startswith('https://'):
        settings.WS_ORIGINS.append(origin.replace('https://', 'wss://'))

settings.CORS_ORIGINS.extend(settings.WS_ORIGINS)
