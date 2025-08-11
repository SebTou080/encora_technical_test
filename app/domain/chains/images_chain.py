"""Images generation chain for optimizing prompts and coordinating generation."""

import json
from pathlib import Path
from typing import Optional

from ...core.logging import get_logger
from ..models.images import ImageGenerateRequest, ImageGenerateResponse
from ...infra.image_providers.hf_inference import HuggingFaceInferenceProvider
from ...infra.storage import storage

logger = get_logger(__name__)


class ImagesChain:
    """Chain for processing image generation requests and optimizing prompts."""

    def __init__(self) -> None:
        """Initialize the images chain."""
        self.hf_provider = HuggingFaceInferenceProvider()
        self.visual_guidelines = self._load_visual_guidelines()

    def _load_visual_guidelines(self) -> str:
        """Load visual guidelines from markdown file."""
        try:
            guidelines_path = Path(__file__).parent.parent / "prompts" / "system_visual.md"
            return guidelines_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"❌ Failed to load visual guidelines: {e}")
            return "Create high-quality, professional product images with natural lighting."

    def _optimize_prompt(self, request: ImageGenerateRequest) -> str:
        """Optimize the image generation prompt based on brand style and aspect ratio."""
        
        base_prompt = request.prompt_brief
        
        # Add brand style if provided
        if request.brand_style:
            try:
                # Try to parse as JSON if it looks like JSON
                if request.brand_style.strip().startswith('{'):
                    brand_data = json.loads(request.brand_style)
                    style_elements = []
                    if 'colors' in brand_data:
                        style_elements.append(f"colors: {', '.join(brand_data['colors'])}")
                    if 'style' in brand_data:
                        style_elements.append(f"style: {brand_data['style']}")
                    if style_elements:
                        base_prompt += f", {', '.join(style_elements)}"
                else:
                    # Treat as plain text description
                    base_prompt += f", {request.brand_style}"
            except json.JSONDecodeError:
                # Fallback to plain text
                base_prompt += f", {request.brand_style}"

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

    def _calculate_dimensions(self, aspect_ratio: str, base_size: int = 1024) -> tuple[int, int]:
        """Calculate image dimensions based on aspect ratio."""
        ratio_map = {
            "1:1": (base_size, base_size),
            "16:9": (base_size, int(base_size * 9 / 16)),
            "9:16": (int(base_size * 9 / 16), base_size),
            "4:3": (base_size, int(base_size * 3 / 4)),
            "3:4": (int(base_size * 3 / 4), base_size),
        }
        
        return ratio_map.get(aspect_ratio.lower(), (base_size, base_size))

    async def generate(self, request: ImageGenerateRequest) -> ImageGenerateResponse:
        """Generate image using Hugging Face Inference API."""
        
        logger.info(f"🎨 Starting image generation: '{request.prompt_brief[:50]}...'")
        
        try:
            # Create job directory
            job_id = storage.create_job_directory()
            
            # Optimize prompt
            optimized_prompt = self._optimize_prompt(request)
            
            # Calculate dimensions
            width, height = self._calculate_dimensions(request.aspect_ratio)
            
            # Generate image using HF provider
            hf_response = await self.hf_provider.generate_image(
                prompt=optimized_prompt,
                seed=request.seed,
                width=width,
                height=height
            )
            
            # Save image to storage
            image_path = storage.save_image(
                job_id=job_id,
                image_bytes=hf_response.image_bytes,
                filename="image.png"
            )
            
            # Prepare metadata
            metadata = {
                "request": request.model_dump(),
                "optimized_prompt": optimized_prompt,
                "original_prompt": request.prompt_brief,
                "generation": hf_response.meta,
                "provider": "hf",
                "model_url": hf_response.model_url,
                "dimensions": {"width": width, "height": height},
                "file_info": {
                    "filename": "image.png",
                    "size_bytes": len(hf_response.image_bytes),
                    "content_type": hf_response.content_type
                }
            }
            
            # Save metadata
            storage.save_metadata(job_id, metadata)
            
            logger.info(f"✨ Image generation completed: {job_id}")
            
            return ImageGenerateResponse(
                job_id=job_id,
                artifact_path=image_path,
                width=width,
                height=height,
                provider="hf",
                model_url=hf_response.model_url,
                meta={
                    "prompt": optimized_prompt,
                    "original_prompt": request.prompt_brief,
                    "negative_prompt": metadata.get("negative_prompt"),
                    "seed": request.seed,
                    "aspect_ratio": request.aspect_ratio,
                    "file_size_bytes": len(hf_response.image_bytes)
                }
            )
            
        except Exception as e:
            logger.error(f"💥 Image generation failed: {e}")
            raise