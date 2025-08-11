"""Hugging Face Inference API provider for image generation."""

import asyncio
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx
from pydantic import BaseModel

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)


class HFImageResponse(BaseModel):
    """Response from Hugging Face image generation."""
    image_bytes: bytes
    content_type: str
    model_url: str
    prompt: str
    seed: Optional[int] = None
    meta: Dict[str, Any]


class HuggingFaceInferenceProvider:
    """Hugging Face Inference API provider for image generation."""
    
    def __init__(self) -> None:
        """Initialize the HF provider."""
        self.model_url = settings.hf_model_url
        self.token = settings.hf_token
        self.timeout = httpx.Timeout(settings.request_timeout_s)
        
        if not self.token:
            logger.warning("⚠️ HF_TOKEN not provided - requests may be rate-limited")

    async def generate_image(
        self,
        prompt: str,
        seed: Optional[int] = None,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        **kwargs: Any
    ) -> HFImageResponse:
        """Generate image using Hugging Face Inference API."""
        
        job_id = str(uuid4())
        logger.info(f"🎨 Starting HF image generation [{job_id[:8]}]: '{prompt[:50]}...'")
        
        # Prepare request payload
        payload = {"inputs": prompt}
        
        # Add parameters if supported by model
        parameters = {}
        if seed is not None:
            parameters["seed"] = seed
        if negative_prompt:
            parameters["negative_prompt"] = negative_prompt
        if width != 1024 or height != 1024:
            parameters["width"] = width
            parameters["height"] = height
            
        if parameters:
            payload["parameters"] = parameters

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"🚀 Calling HF Inference API for [{job_id[:8]}]...")
                
                response = await client.post(
                    self.model_url,
                    json=payload,
                    headers=headers
                )
                
                # Handle rate limiting or model loading
                if response.status_code == 503:
                    logger.warning(f"⏳ Model loading for [{job_id[:8]}], retrying in 20s...")
                    await asyncio.sleep(20)
                    response = await client.post(
                        self.model_url,
                        json=payload,
                        headers=headers
                    )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"❌ HF API error [{job_id[:8]}]: {response.status_code} - {error_detail}")
                    raise Exception(f"HF API error: {response.status_code} - {error_detail}")
                
                # Get content type
                content_type = response.headers.get("content-type", "image/png")
                image_bytes = response.content
                
                logger.info(f"✨ HF image generated [{job_id[:8]}]: {len(image_bytes)} bytes")
                
                return HFImageResponse(
                    image_bytes=image_bytes,
                    content_type=content_type,
                    model_url=self.model_url,
                    prompt=prompt,
                    seed=seed,
                    meta={
                        "job_id": job_id,
                        "negative_prompt": negative_prompt,
                        "width": width,
                        "height": height,
                        "response_size_bytes": len(image_bytes),
                        "parameters": parameters
                    }
                )
                
        except httpx.TimeoutException:
            logger.error(f"⏰ HF API timeout for [{job_id[:8]}] after {settings.request_timeout_s}s")
            raise Exception(f"HF API timeout after {settings.request_timeout_s}s")
        except httpx.RequestError as e:
            logger.error(f"🌐 HF API connection error for [{job_id[:8]}]: {e}")
            raise Exception(f"HF API connection error: {e}")
        except Exception as e:
            logger.error(f"💥 HF image generation failed for [{job_id[:8]}]: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if HF Inference API is accessible."""
        try:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
                
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                # Try a minimal request to check API availability
                response = await client.post(
                    self.model_url,
                    json={"inputs": "test"},
                    headers=headers
                )
                
                # Any response (even 503 for model loading) means API is reachable
                return response.status_code in [200, 503, 422, 400]
                
        except Exception as e:
            logger.error(f"🚨 HF API health check failed: {e}")
            return False