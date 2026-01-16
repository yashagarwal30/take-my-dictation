"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    PROJECT_NAME: str = "Take My Dictation API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Voice recording app with AI-powered transcription and summaries"

    # Database
    DATABASE_URL: str

    # API Keys
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str

    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"  # Change in .env for production

    # Razorpay Payment Gateway
    RAZORPAY_KEY_ID: str = ""  # API Key ID (public key)
    RAZORPAY_KEY_SECRET: str = ""  # API Key Secret (private key)
    RAZORPAY_WEBHOOK_SECRET: str = ""  # Webhook signature secret

    # Email Service Configuration
    EMAIL_SERVICE: str = "sendgrid"  # 'sendgrid' or 'ses'
    SENDGRID_API_KEY: str = ""
    # AWS SES Configuration (if using ses)
    AWS_SES_REGION: str = "us-east-1"
    AWS_SES_ACCESS_KEY_ID: str = ""
    AWS_SES_SECRET_ACCESS_KEY: str = ""
    EMAIL_FROM_ADDRESS: str = "noreply@takemydictation.ai"
    EMAIL_FROM_NAME: str = "Take My Dictation"

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB

    # Audio Processing
    ALLOWED_AUDIO_FORMATS: str = "mp3,wav,m4a,ogg,flac,webm"

    # Redis Configuration (for rate limiting and caching)
    REDIS_URL: str = ""  # Optional: If not set, in-memory rate limiting is used

    # JWT Configuration
    JWT_SECRET_KEY: str = ""  # Will fallback to SECRET_KEY if not set
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    TRIAL_TOKEN_EXPIRE_HOURS: int = 24

    # Trial Configuration
    TRIAL_MINUTES_LIMIT: int = 10

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH: int = 5  # per minute
    RATE_LIMIT_TRIAL: int = 10  # per minute
    RATE_LIMIT_UPLOAD: int = 20  # per minute

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

    @property
    def allowed_formats_list(self) -> List[str]:
        """Convert comma-separated formats to list."""
        return [fmt.strip() for fmt in self.ALLOWED_AUDIO_FORMATS.split(",")]

    @property
    def jwt_secret(self) -> str:
        """Get JWT secret key, fallback to SECRET_KEY if not set."""
        return self.JWT_SECRET_KEY or self.SECRET_KEY

    @property
    def is_redis_enabled(self) -> bool:
        """Check if Redis is configured."""
        return bool(self.REDIS_URL)

    @property
    def is_email_configured(self) -> bool:
        """Check if email service is properly configured."""
        if self.EMAIL_SERVICE == "sendgrid":
            return bool(self.SENDGRID_API_KEY)
        elif self.EMAIL_SERVICE == "ses":
            return bool(self.AWS_SES_ACCESS_KEY_ID and self.AWS_SES_SECRET_ACCESS_KEY)
        return False


# Global settings instance
settings = Settings()
