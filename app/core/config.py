import json

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    EMAIL_BACKEND: str = "console"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@efektywniejsi.pl"
    SMTP_FROM_NAME: str = "Efektywniejsi"

    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    BACKEND_CORS_ORIGINS: str = (
        '["http://localhost:5173","http://localhost:3000","http://localhost:3001"]'
    )

    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Efektywniejsi Ekosystem Auth API"
    DEBUG: bool = False

    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    MUX_TOKEN_ID: str = ""
    MUX_TOKEN_SECRET: str = ""
    MUX_WEBHOOK_SECRET: str | None = None

    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 8192
    ANTHROPIC_TEMPERATURE: float = 0.7
    ANTHROPIC_MAX_TOKENS_SALES_PAGE: int = 16384

    PAYU_MERCHANT_ID: str = ""
    PAYU_SECRET_KEY: str = ""
    PAYU_API_URL: str = "https://secure.payu.com"
    PAYU_WEBHOOK_SECRET: str = ""

    TOTP_ENCRYPTION_KEY: str = ""

    # Fakturownia (Polish invoicing service)
    # Invoice is created and sent automatically via Fakturownia email
    FAKTUROWNIA_API_TOKEN: str = ""
    FAKTUROWNIA_SUBDOMAIN: str = ""  # e.g., "mycompany" for mycompany.fakturownia.pl
    FAKTUROWNIA_SELLER_NAME: str = ""
    FAKTUROWNIA_SELLER_TAX_NO: str = ""  # NIP
    FAKTUROWNIA_SELLER_STREET: str = ""
    FAKTUROWNIA_SELLER_POST_CODE: str = ""
    FAKTUROWNIA_SELLER_CITY: str = ""
    FAKTUROWNIA_SELLER_COUNTRY: str = "PL"

    # Cloudflare R2 storage (S3-compatible)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "efektywniejsi-uploads"
    R2_PUBLIC_URL: str = ""  # e.g. https://files.efektywniejsi.pl

    # Storage backend: "local" for development, "r2" for production
    STORAGE_BACKEND: str = "local"

    # Storage cleanup settings
    STORAGE_CLEANUP_GRACE_HOURS: int = 24  # Don't delete files newer than this
    STORAGE_CLEANUP_BATCH_SIZE: int = 100  # Files to process per batch
    STORAGE_CLEANUP_DRY_RUN: bool = False  # Default to actual deletion in production

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def cors_origins(self) -> list[str]:
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            try:
                parsed: list[str] = json.loads(self.BACKEND_CORS_ORIGINS)
                return parsed
            except json.JSONDecodeError:
                return ["http://localhost:5173", "http://localhost:3000"]
        return self.BACKEND_CORS_ORIGINS

    @property
    def r2_endpoint_url(self) -> str:
        return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"


settings = Settings()
