"""Configuration management using Pydantic settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration with environment variable support."""

    # OpenAI Configuration
    openai_api_key: str = Field(default="changeme", description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-4o", description="OpenAI model name for text generation"
    )
    openai_image_model: str = Field(
        default="dall-e-3", description="OpenAI model name for image generation"
    )

    # LangSmith Configuration
    langchain_tracing_v2: bool = Field(
        default=False, description="Enable LangSmith tracing"
    )
    langchain_api_key: str | None = Field(default=None, description="LangSmith API key")
    langchain_project: str = Field(
        default="pr-crazy-subset-65", description="LangSmith project name"
    )
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com", description="LangSmith endpoint"
    )

    # Server Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    frontend_port: int = Field(default=7860, description="Frontend port")

    # Request Configuration
    request_timeout_s: int = Field(default=60, description="Request timeout in seconds")
    max_concurrency: int = Field(default=5, description="Maximum concurrent requests")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level")

    class Config:
        env_file = "configs/.env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
