"""Images generation chain for optimizing prompts and coordinating generation."""

import json
from pathlib import Path
from typing import Optional

from langsmith import traceable

from ...core.logging import get_logger
from ...core.langsmith import LangSmithTracer
from ..models.images import ImageGenerateRequest, ImageGenerateResponse
from ...infra.image_providers.openai_dalle import OpenAIImageProvider
from ...infra.storage import storage

logger = get_logger(__name__)


class ImagesChain:
    """Chain for processing image generation requests and optimizing prompts."""

    def __init__(self) -> None:
        """Initialize the images chain."""
        self.openai_provider = OpenAIImageProvider()
        self.visual_guidelines = self._load_visual_guidelines()

    def _load_visual_guidelines(self) -> str:
        """Load visual guidelines from markdown file."""
        try:
            guidelines_path = Path(__file__).parent.parent / "prompts" / "system_visual.md"
            return guidelines_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"❌ Failed to load visual guidelines: {e}")
            return "Create high-quality, professional product images with natural lighting."

    @traceable(
        run_type="llm",
        name="optimize-image-prompt"
    )
    def _optimize_prompt(self, request: ImageGenerateRequest) -> str:
        """Optimize the image generation prompt based on aspect ratio."""
        
        base_prompt = request.prompt_brief

        # Optimize based on aspect ratio
        aspect_ratio = request.aspect_ratio.lower()
        
        if aspect_ratio == "1:1":
            # Square format - good for social media
            optimized_prompt = (
                f"Professional product photography of {base_prompt}, "
                "centered composition, clean background, soft natural lighting, "
                "high resolution, commercial quality, square format"
            )
        elif aspect_ratio == "16:9":
            # Horizontal format - good for banners
            optimized_prompt = (
                f"Wide angle product photography of {base_prompt}, "
                "horizontal composition, space for text, dynamic layout, "
                "professional lighting, banner format, marketing quality"
            )
        elif aspect_ratio == "9:16":
            # Vertical format - good for stories/mobile
            optimized_prompt = (
                f"Vertical product photography of {base_prompt}, "
                "portrait composition, mobile-friendly layout, "
                "natural lighting, social media optimized, story format"
            )
        else:
            # Default optimization
            optimized_prompt = (
                f"Professional product photography of {base_prompt}, "
                "clean composition, natural lighting, high quality, commercial grade"
            )

        # Add quality and style improvements
        optimized_prompt += (
            ", photorealistic, detailed texture, vibrant but natural colors, "
            "professional food photography, studio quality"
        )

        logger.info(f"🎯 Optimized prompt ({aspect_ratio}): '{optimized_prompt[:100]}...'")
        return optimized_prompt

    def _get_openai_size(self, aspect_ratio: str) -> str:
        """Get OpenAI DALL-E compatible size from aspect ratio."""
        ratio_map = {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792",
            "4:3": "1024x1024",  # Closest match
            "3:4": "1024x1024",  # Closest match
        }
        
        return ratio_map.get(aspect_ratio.lower(), "1024x1024")

    def _calculate_dimensions(self, aspect_ratio: str, base_size: int = 1024) -> tuple[int, int]:
        """Calculate image dimensions from OpenAI size."""
        size_str = self._get_openai_size(aspect_ratio)
        width, height = map(int, size_str.split('x'))
        return width, height

    @traceable(
        run_type="chain",
        name="healthy-snack-ia-image-generation"
    )
    async def generate(self, request: ImageGenerateRequest) -> ImageGenerateResponse:
        """Generate image using OpenAI DALL-E API."""
        
        logger.info(f"🎨 Starting image generation: '{request.prompt_brief[:50]}...'")
        
        try:
            # Create job directory
            job_id = storage.create_job_directory()
            
            # Optimize prompt
            optimized_prompt = self._optimize_prompt(request)
            
            # Get OpenAI size and calculate dimensions
            openai_size = self._get_openai_size(request.aspect_ratio)
            width, height = self._calculate_dimensions(request.aspect_ratio)
            
            # Generate image using OpenAI provider
            openai_response = await self.openai_provider.generate_image(
                prompt=optimized_prompt,
                size=openai_size,
                quality="hd",
                style="natural"
            )
            
            # Save image to storage
            image_path = storage.save_image(
                job_id=job_id,
                image_bytes=openai_response.image_bytes,
                filename="image.png"
            )
            
            # Prepare metadata
            metadata = {
                "request": request.model_dump(),
                "optimized_prompt": optimized_prompt,
                "original_prompt": request.prompt_brief,
                "revised_prompt": openai_response.revised_prompt,
                "generation": openai_response.meta,
                "provider": "openai",
                "model": openai_response.model,
                "dimensions": {"width": width, "height": height},
                "file_info": {
                    "filename": "image.png",
                    "size_bytes": len(openai_response.image_bytes),
                    "content_type": openai_response.content_type
                }
            }
            
            # Save metadata
            storage.save_metadata(job_id, metadata)
            
            logger.info(f"✨ Image generation completed: {job_id}")
            
            return ImageGenerateResponse(
                job_id=job_id,
                artifact_path=image_path,
                width=width,
                height=height
            )
            
        except Exception as e:
            logger.error(f"💥 Image generation failed: {e}")
            raise