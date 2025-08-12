"""LangSmith tracing configuration and utilities."""

import os
from typing import Optional

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


def configure_langsmith() -> None:
    """Configure LangSmith tracing with environment variables."""
    
    # Only configure if tracing is enabled and API key is provided
    if not settings.langchain_tracing_v2:
        logger.info("🔍 LangSmith tracing disabled")
        return
    
    if not settings.langchain_api_key or settings.langchain_api_key == "changeme":
        logger.warning("⚠️ LangSmith API key not configured - tracing disabled")
        return
    
    # Set environment variables for LangSmith
    os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2).lower()
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
    
    logger.info(f"🔍 LangSmith tracing enabled for project: {settings.langchain_project}")
    logger.info(f"📡 LangSmith endpoint: {settings.langchain_endpoint}")


def get_run_tags() -> list[str]:
    """Get standard tags for LangSmith runs."""
    return [
        "healthy-snack-ia",
        "fastapi",
        "langchain",
        f"model:{settings.openai_model}",
        "production"
    ]


def get_run_metadata() -> dict:
    """Get standard metadata for LangSmith runs."""
    return {
        "app_version": "0.1.0",
        "openai_model": settings.openai_model,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "request_timeout": settings.request_timeout_s,
        "max_concurrency": settings.max_concurrency
    }


class LangSmithTracer:
    """Utility class for managing LangSmith tracing contexts."""
    
    @staticmethod
    def get_trace_config(operation_name: str, **kwargs) -> dict:
        """Get trace configuration for a specific operation."""
        return {
            "run_name": f"healthy-snack-ia-{operation_name}",
            "tags": get_run_tags() + [operation_name],
            "metadata": {
                **get_run_metadata(),
                **kwargs
            }
        }
    
    @staticmethod
    def get_descriptions_config(product_name: str, channels: list[str]) -> dict:
        """Get trace configuration for descriptions generation."""
        return LangSmithTracer.get_trace_config(
            "descriptions",
            product_name=product_name,
            channels=channels,
            operation_type="content_generation"
        )
    
    @staticmethod
    def get_feedback_config(total_comments: int) -> dict:
        """Get trace configuration for feedback analysis."""
        return LangSmithTracer.get_trace_config(
            "feedback_analysis",
            total_comments=total_comments,
            operation_type="sentiment_analysis"
        )
    
    @staticmethod
    def get_images_config(prompt: str, aspect_ratio: str) -> dict:
        """Get trace configuration for image generation."""
        return LangSmithTracer.get_trace_config(
            "image_generation",
            prompt_length=len(prompt),
            aspect_ratio=aspect_ratio,
            operation_type="image_generation"
        )