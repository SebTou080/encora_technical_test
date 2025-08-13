"""OpenAI DALL-E provider for image generation."""

from typing import Any
from uuid import uuid4

import httpx
from langsmith import traceable
from pydantic import BaseModel

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)


class OpenAIImageResponse(BaseModel):
    """Response from OpenAI DALL-E image generation."""

    image_bytes: bytes
    content_type: str
    model: str
    prompt: str
    revised_prompt: str | None = None
    meta: dict[str, Any]


class OpenAIImageProvider:
    """OpenAI DALL-E provider for image generation."""

    def __init__(self) -> None:
        """Initialize the OpenAI provider."""
        self.model = settings.openai_image_model
        self.api_key = settings.openai_api_key
        self.timeout = httpx.Timeout(settings.request_timeout_s)
        self.base_url = "https://api.openai.com/v1/images/generations"

        if not self.api_key or self.api_key == "changeme":
            logger.warning("⚠️ OpenAI API key not provided - image generation will fail")

    @traceable(run_type="llm", name="openai-dalle-generate")
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "natural",
        **kwargs: Any,
    ) -> OpenAIImageResponse:
        """Generate image using OpenAI DALL-E API."""

        job_id = str(uuid4())
        logger.info(
            f"🎨 Starting OpenAI image generation [{job_id[:8]}]: '{prompt[:50]}...'"
        )

        # Prepare request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality,
            "style": style,
            "response_format": "url",
        }

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"🚀 Calling OpenAI DALL-E API for [{job_id[:8]}]...")

                response = await client.post(
                    self.base_url, json=payload, headers=headers
                )

                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        f"❌ OpenAI API error [{job_id[:8]}]: {response.status_code} - {error_detail}"
                    )
                    raise Exception(
                        f"OpenAI API error: {response.status_code} - {error_detail}"
                    )

                # Parse response
                response_data = response.json()
                image_data = response_data["data"][0]
                image_url = image_data["url"]
                revised_prompt = image_data.get("revised_prompt")

                # Download the generated image
                logger.info(f"📥 Downloading generated image for [{job_id[:8]}]...")
                image_response = await client.get(image_url)

                if image_response.status_code != 200:
                    logger.error(
                        f"❌ Failed to download image [{job_id[:8]}]: {image_response.status_code}"
                    )
                    raise Exception(
                        f"Failed to download generated image: {image_response.status_code}"
                    )

                image_bytes = image_response.content
                content_type = image_response.headers.get("content-type", "image/png")

                logger.info(
                    f"✨ OpenAI image generated [{job_id[:8]}]: {len(image_bytes)} bytes"
                )

                return OpenAIImageResponse(
                    image_bytes=image_bytes,
                    content_type=content_type,
                    model=self.model,
                    prompt=prompt,
                    revised_prompt=revised_prompt,
                    meta={
                        "job_id": job_id,
                        "size": size,
                        "quality": quality,
                        "style": style,
                        "response_size_bytes": len(image_bytes),
                        "original_url": image_url,
                    },
                )

        except httpx.TimeoutException:
            logger.error(
                f"⏰ OpenAI API timeout for [{job_id[:8]}] after {settings.request_timeout_s}s"
            )
            raise Exception(f"OpenAI API timeout after {settings.request_timeout_s}s")
        except httpx.RequestError as e:
            logger.error(f"🌐 OpenAI API connection error for [{job_id[:8]}]: {e}")
            raise Exception(f"OpenAI API connection error: {e}")
        except Exception as e:
            logger.error(f"💥 OpenAI image generation failed for [{job_id[:8]}]: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                # Test with a minimal request to models endpoint
                response = await client.get(
                    "https://api.openai.com/v1/models", headers=headers
                )

                # Check if we can access the API (200 or some expected error codes)
                return response.status_code in [200, 401, 429]

        except Exception as e:
            logger.error(f"🚨 OpenAI API health check failed: {e}")
            return False
