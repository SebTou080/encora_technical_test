"""Image generation request and response models."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """Request for generating promotional images."""
    prompt_brief: str = Field(..., description="Image generation prompt")
    aspect_ratio: str = Field("1:1", description="Image aspect ratio")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")


class ImageGenerateResponse(BaseModel):
    """Response from image generation."""
    job_id: str = Field(..., description="Unique job identifier")
    artifact_path: str = Field(..., description="Path to generated image")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")