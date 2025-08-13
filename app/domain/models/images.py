"""Image generation request and response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """Request for generating promotional images."""
    prompt_brief: str = Field(..., description="Image generation prompt")
    aspect_ratio: str = Field("1:1", description="Image aspect ratio")
    cantidad_imagenes: int = Field(1, ge=1, le=3, description="Number of images to generate (1-3)")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")


class ImageGenerateResponse(BaseModel):
    """Response from image generation."""
    job_id: str = Field(..., description="Unique job identifier")
    artifact_paths: List[str] = Field(..., description="Paths to generated images")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")