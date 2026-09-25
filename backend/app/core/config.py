"""Centralised settings, loaded from environment variables / backend/.env.

Every field here mirrors the `backend/.env` block in Implementation_Plan.md
section 16. Fields that name external services (Supabase, Groq, Sepolia RPC,
relayer key, encryption keys, Brevo, Sentry) are all Optional[str] so the app
can boot with a placeholder/empty .env in a dev sandbox that lacks real
credentials -- callers must check `settings.<flag>_configured` (see
`is_configured`) or rely on the individual service wrappers degrading
gracefully with a structlog warning rather than crashing at import time.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- App ---
    ENV: str = "development"
    DEMO_MODE: bool = True
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    API_V1_PREFIX: str = "/api/v1"

    # --- Supabase ---
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWKS_URL: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None

    # --- Groq ---
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL_AGENT: str = "openai/gpt-oss-120b"
    GROQ_MODEL_AGENT_FALLBACK: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_EXTRACT: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_EXTRACT_FALLBACK: str = "gpt-oss-20b"
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"
    GROQ_MODEL_FAST_FALLBACK: str = "gpt-oss-20b"
    GROQ_MODEL_VISION: str = "qwen/qwen3.8-27b"
    GROQ_MODEL_STT: str = "whisper-large-v3"
    GROQ_MODEL_STT_FALLBACK: str = "whisper-large-v3-turbo"
    SARVAM_API_KEY: Optional[str] = None

    # --- Chain ---
    SEPOLIA_RPC_URL: Optional[str] = None
    SEPOLIA_RPC_FALLBACK: str = "https://ethereum-sepolia-rpc.publicnode.com"
    CHAIN_ID: int = 11155111
    RELAYER_PRIVATE_KEY: Optional[str] = None
    REGISTRY_ADDRESS: Optional[str] = None
    CREDENTIAL_ADDRESS: Optional[str] = None
    LEDGER_ADDRESS: Optional[str] = None
    REGISTRY_DEPLOY_BLOCK: int = 0

    # --- Crypto keys (Fernet) ---
    WALLET_ENC_KEY: Optional[str] = None
    ESCROW_KEY: Optional[str] = None
    RECOVERY_KEY: Optional[str] = None
    CRON_SECRET: Optional[str] = "dev-cron-secret"

    # --- Email ---
    BREVO_API_KEY: Optional[str] = None
    MAIL_FROM: str = "virasat.demo@gmail.com"
    SENTRY_DSN: Optional[str] = None

    # --- Rate limits ---
    RATE_LIMIT_AI: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "20/minute"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_ROLE_KEY)

    @property
    def groq_configured(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def chain_configured(self) -> bool:
        return bool(self.SEPOLIA_RPC_URL and self.REGISTRY_ADDRESS and self.RELAYER_PRIVATE_KEY)

    @property
    def wallet_enc_configured(self) -> bool:
        return bool(self.WALLET_ENC_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
