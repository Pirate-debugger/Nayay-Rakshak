import logging
import os
import re
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("nyaya_rakshak.config")

# Known insecure/development placeholder secret keys that MUST NEVER be used in production
INSECURE_DEV_SECRETS = {
    "nyaya-rakshak-secure-dev-secret-key-min32chars-for-jwt-signing!",
    "secret",
    "changeme",
    "password",
    "default-secret-key",
    "12345678901234567890123456789012",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    PROJECT_NAME: str = "Nyaya Rakshak - AI Legal Clarity, Verification & Action Navigator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Security & Auth
    # Notice: In non-production, a designated dev key is permitted. In production, validate_production_settings() enforces explicit, high-entropy configuration.
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "nyaya-rakshak-secure-dev-secret-key-min32chars-for-jwt-signing!"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    )  # 15 minutes for access tokens
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # 7 days
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1")

    # Storage & Uploads
    QUARANTINE_DIR: str = os.getenv("QUARANTINE_DIR", "./storage/quarantine")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./storage/documents")
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"]
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "image/png",
        "image/jpeg",
    ]

    # Malware & Antivirus Scanning
    ENABLE_CLAMAV_SCAN: bool = os.getenv("ENABLE_CLAMAV_SCAN", "false").lower() in ("true", "1")
    CLAMAV_HOST: str = os.getenv("CLAMAV_HOST", "localhost")
    CLAMAV_PORT: int = int(os.getenv("CLAMAV_PORT", "3310"))
    CLAMAV_REQUIRED: bool = os.getenv("CLAMAV_REQUIRED", "false").lower() in ("true", "1")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./nyaya_rakshak.db")

    # AI Provider Configuration
    # Options: "mock" (offline rule-based), "gemini"
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "mock")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Privacy & PII
    PRIVACY_DEFAULT_REDACT_PII: bool = True

    # Rate Limiting (Redis or in-memory)
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "10/minute")
    RATE_LIMIT_REGISTER: str = os.getenv("RATE_LIMIT_REGISTER", "5/minute")
    RATE_LIMIT_UPLOAD: str = os.getenv("RATE_LIMIT_UPLOAD", "15/minute")
    RATE_LIMIT_ANALYSIS: str = os.getenv("RATE_LIMIT_ANALYSIS", "30/minute")
    RATE_LIMIT_QA: str = os.getenv("RATE_LIMIT_QA", "30/minute")
    RATE_LIMIT_COMPARISON: str = os.getenv("RATE_LIMIT_COMPARISON", "20/minute")
    RATE_LIMIT_VERIFICATION: str = os.getenv("RATE_LIMIT_VERIFICATION", "30/minute")
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
    RATE_LIMIT_AUTH_PER_MINUTE: str = "10/minute"

    # Distributed Rate Limiting Backend (Redis)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", None)

    # Demo & Sample Features Control
    ENABLE_DEMO_ACCOUNTS: bool = os.getenv("ENABLE_DEMO_ACCOUNTS", "false").lower() in ("true", "1")
    ENABLE_SAMPLE_DOCUMENTS: bool = os.getenv("ENABLE_SAMPLE_DOCUMENTS", "true").lower() in (
        "true",
        "1",
    )

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    def validate_production_settings(self) -> None:
        """
        Fail fast in production if security configurations are weak, missing, or defaulted.
        """
        if not self.is_production():
            return

        # 1. Validate SECRET_KEY in production
        if not self.SECRET_KEY or self.SECRET_KEY in INSECURE_DEV_SECRETS:
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY must be explicitly set to a unique, "
                "cryptographically random string in production. Default/development keys are strictly forbidden."
            )

        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                f"CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY length is {len(self.SECRET_KEY)} characters. "
                "Production SECRET_KEY must be at least 32 characters long."
            )

        # Check entropy (require at least 2 character classes)
        has_lower = bool(re.search(r"[a-z]", self.SECRET_KEY))
        has_upper = bool(re.search(r"[A-Z]", self.SECRET_KEY))
        has_digit = bool(re.search(r"[0-9]", self.SECRET_KEY))
        has_special = bool(re.search(r"[^a-zA-Z0-9]", self.SECRET_KEY))
        if sum([has_lower, has_upper, has_digit, has_special]) < 2:
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY entropy too low. "
                "Must combine letters, numbers, or special characters."
            )

        # 2. Validate CORS in production
        if "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Wildcard '*' CORS origin is strictly forbidden in production with credentials."
            )
        for origin in self.CORS_ORIGINS:
            if "localhost" in origin or "127.0.0.1" in origin:
                logger.warning(
                    f"Production warning: CORS_ORIGINS contains local origin '{origin}'. "
                    "Ensure production environment variables restrict this to trusted public domains."
                )

        # 3. Validate Cookie Security
        if not self.COOKIE_SECURE:
            logger.warning(
                "Production warning: COOKIE_SECURE is False. In production, COOKIE_SECURE must be True for HTTPS."
            )


settings = Settings()
