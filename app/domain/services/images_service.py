"""Service layer for image generation and management."""

from typing import Optional

from ...core.logging import get_logger
from ..chains.images_chain import ImagesChain
from ..models.images import ImageGenerateRequest, ImageGenerateResponse
from ...infra.image_providers.hf_inference import HuggingFaceInferenceProvider
from ...infra.storage import storage

logger = get_logger(__name__)


class ImagesService:
    """Service for orchestrating image generation and management."""

    def __init__(self) -> None:
        """Initialize the images service."""
        self.chain = ImagesChain()
        self.hf_provider = HuggingFaceInferenceProvider()

    async def generate_image(self, request: ImageGenerateRequest) -> ImageGenerateResponse:
        """Generate promotional image using the images chain."""
        
        logger.info(f"🎨 Starting image generation for: '{request.prompt_brief[:50]}...'")
        
        try:
            # Validate aspect ratio
            supported_ratios = ["1:1", "16:9", "9:16", "4:3", "3:4"]
            if request.aspect_ratio not in supported_ratios:
                raise ValueError(f"Unsupported aspect ratio: {request.aspect_ratio}. Supported: {supported_ratios}")

            # Validate seed range if provided
            if request.seed is not None and (request.seed < 0 or request.seed > 2147483647):
                raise ValueError("Seed must be between 0 and 2147483647")

            # Generate image using chain
            result = await self.chain.generate(request)
            
            logger.info(f"🎉 Successfully generated image: {result.job_id}")
            return result

        except Exception as e:
            logger.error(f"💥 Image generation failed: {e}")
            raise

    async def health_check(self) -> dict:
        """Check health of image generation services."""
        
        logger.info("🔍 Checking image services health...")
        
        try:
            # Check HF provider
            hf_healthy = await self.hf_provider.health_check()
            
            # Check storage
            storage_stats = storage.get_storage_stats()
            storage_healthy = "error" not in storage_stats
            
            health_status = {
                "status": "healthy" if (hf_healthy and storage_healthy) else "degraded",
                "services": {
                    "huggingface_inference": {
                        "status": "healthy" if hf_healthy else "unhealthy",
                        "provider": "huggingface",
                        "model_url": self.hf_provider.model_url
                    },
                    "storage": {
                        "status": "healthy" if storage_healthy else "unhealthy",
                        **storage_stats
                    }
                }
            }
            
            if health_status["status"] == "healthy":
                logger.info("✅ Image services health check passed")
            else:
                logger.warning("⚠️ Image services health check shows degraded status")
            
            return health_status
            
        except Exception as e:
            logger.error(f"❌ Image services health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def get_artifact_info(self, job_id: str) -> Optional[dict]:
        """Get information about generated artifacts."""
        
        try:
            # Load metadata
            metadata = storage.load_metadata(job_id)
            if not metadata:
                return None
                
            # List artifacts
            artifacts = storage.list_job_artifacts(job_id)
            
            return {
                "job_id": job_id,
                "artifacts": artifacts,
                "metadata": metadata,
                "paths": {
                    artifact: storage.get_artifact_path(job_id, artifact)
                    for artifact in artifacts
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get artifact info for {job_id}: {e}")
            return None

    async def regenerate_image(
        self, 
        job_id: str, 
        modifications: Optional[dict] = None
    ) -> Optional[ImageGenerateResponse]:
        """Regenerate image with optional modifications."""
        
        try:
            # Load original metadata
            metadata = storage.load_metadata(job_id)
            if not metadata or "request" not in metadata:
                logger.error(f"❌ Cannot regenerate: missing metadata for {job_id}")
                return None
            
            # Reconstruct original request
            original_request_data = metadata["request"]
            
            # Apply modifications if provided
            if modifications:
                original_request_data.update(modifications)
            
            # Create new request
            new_request = ImageGenerateRequest(**original_request_data)
            
            logger.info(f"🔄 Regenerating image based on {job_id}")
            
            # Generate new image
            return await self.generate_image(new_request)
            
        except Exception as e:
            logger.error(f"💥 Image regeneration failed for {job_id}: {e}")
            return None