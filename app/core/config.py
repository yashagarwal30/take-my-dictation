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

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB

    # Audio Processing
    ALLOWED_AUDIO_FORMATS: str = "mp3,wav,m4a,ogg,flac,webm"

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


# Global settings instance
settings = Settings()
