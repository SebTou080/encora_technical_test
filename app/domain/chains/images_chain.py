"""Images generation chain for optimizing prompts and coordinating generation."""

import asyncio
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

    def _create_variation_prompt(self, base_prompt: str, variation_index: int, aspect_ratio: str) -> str:
        """Create variation of the base prompt for multiple image generation."""
        
        # Base optimization
        aspect_ratio = aspect_ratio.lower()
        
        if aspect_ratio == "1:1":
            format_desc = "centered composition, square format"
        elif aspect_ratio == "16:9":
            format_desc = "horizontal composition, banner format"
        elif aspect_ratio == "9:16":
            format_desc = "vertical composition, story format"
        else:
            format_desc = "clean composition"
        
        # Variation templates
        variations = [
            # Variation 1: Clean, centered
            f"Professional product photography of {base_prompt}, {format_desc}, clean white background, soft natural lighting, high resolution, commercial quality",
            
            # Variation 2: Natural surface, angled
            f"Professional product photography of {base_prompt}, {format_desc}, natural wood surface, 15-degree angle perspective, warm ambient lighting, rustic elegance",
            
            # Variation 3: Lifestyle context
            f"Professional product photography of {base_prompt}, {format_desc}, lifestyle context with fresh ingredients around, overhead view, marble surface, natural daylight"
        ]
        
        # Get the appropriate variation (cycle if more than 3)
        variation_prompt = variations[variation_index % len(variations)]
        
        # Add quality improvements
        variation_prompt += (
            ", photorealistic, detailed texture, vibrant but natural colors, "
            "professional food photography, studio quality"
        )
        
        logger.info(f"🎯 Variation {variation_index + 1} prompt: '{variation_prompt[:100]}...'")
        return variation_prompt

    @traceable(
        run_type="chain",
        name="healthy-snack-ia-image-generation"
    )
    async def generate(self, request: ImageGenerateRequest) -> ImageGenerateResponse:
        """Generate multiple images using OpenAI DALL-E API."""
        
        logger.info(f"🎨 Starting generation of {request.cantidad_imagenes} image(s): '{request.prompt_brief[:50]}...'")
        
        try:
            # Create job directory
            job_id = storage.create_job_directory()
            
            # Get OpenAI size and calculate dimensions
            openai_size = self._get_openai_size(request.aspect_ratio)
            width, height = self._calculate_dimensions(request.aspect_ratio)
            
            # Generate multiple images in parallel
            async def generate_single_image(i: int):
                """Generate a single image with error handling."""
                try:
                    logger.info(f"🖼️ Generating image {i + 1}/{request.cantidad_imagenes}")
                    
                    # Create variation prompt
                    variation_prompt = self._create_variation_prompt(
                        request.prompt_brief, i, request.aspect_ratio
                    )
                    
                    # Generate image using OpenAI provider
                    openai_response = await self.openai_provider.generate_image(
                        prompt=variation_prompt,
                        size=openai_size,
                        quality="hd",
                        style="natural"
                    )
                    
                    # Save image to storage with unique filename
                    filename = f"image_{i + 1}.png"
                    image_path = storage.save_image(
                        job_id=job_id,
                        image_bytes=openai_response.image_bytes,
                        filename=filename
                    )
                    
                    # Prepare metadata for this image
                    image_metadata = {
                        "variation_index": i + 1,
                        "filename": filename,
                        "variation_prompt": variation_prompt,
                        "original_prompt": request.prompt_brief,
                        "revised_prompt": openai_response.revised_prompt,
                        "generation": openai_response.meta,
                        "provider": "openai",
                        "model": openai_response.model,
                        "file_info": {
                            "size_bytes": len(openai_response.image_bytes),
                            "content_type": openai_response.content_type
                        }
                    }
                    
                    return image_path, image_metadata
                    
                except Exception as e:
                    logger.error(f"❌ Failed to generate image {i + 1}: {e}")
                    return None, None
            
            # Create tasks for parallel execution
            tasks = [generate_single_image(i) for i in range(request.cantidad_imagenes)]
            
            # Execute all image generations in parallel
            logger.info(f"🚀 Starting parallel generation of {request.cantidad_imagenes} images")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            image_paths = []
            all_metadata = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Image {i + 1} generation failed with exception: {result}")
                    continue
                    
                image_path, metadata = result
                if image_path and metadata:
                    image_paths.append(image_path)
                    all_metadata.append(metadata)
                else:
                    logger.warning(f"⚠️ Image {i + 1} generation returned empty result")
            
            # Ensure we have at least one successful image
            if not image_paths:
                raise Exception("Failed to generate any images successfully")
            
            # Prepare complete metadata
            complete_metadata = {
                "request": request.model_dump(),
                "dimensions": {"width": width, "height": height},
                "total_images": request.cantidad_imagenes,
                "images": all_metadata
            }
            
            # Save metadata
            storage.save_metadata(job_id, complete_metadata)
            
            logger.info(f"✨ Generated {len(image_paths)} images successfully: {job_id}")
            
            return ImageGenerateResponse(
                job_id=job_id,
                artifact_paths=image_paths,
                width=width,
                height=height
            )
            
        except Exception as e:
            logger.error(f"💥 Image generation failed: {e}")
            raise