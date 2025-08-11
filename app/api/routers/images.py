"""Images API router."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from ...core.logging import get_correlation_id, get_logger
from ...domain.models.images import ImageGenerateRequest, ImageGenerateResponse
from ...domain.services.images_service import ImagesService
from ..deps import get_images_service
from ..errors import ServiceError, ValidationError

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/images", tags=["images"])


def get_images_service() -> ImagesService:
    """Get images service instance."""
    return ImagesService()


@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image(
    prompt_brief: str = Form(..., description="Image generation prompt"),
    brand_style: Optional[str] = Form(None, description="Brand style guidelines (JSON or text)"),
    aspect_ratio: str = Form("1:1", description="Image aspect ratio"),
    seed: Optional[int] = Form(None, description="Random seed for reproducibility"),
    reference_image: Optional[UploadFile] = File(None, description="Reference image (optional)"),
    service: ImagesService = Depends(get_images_service),
) -> ImageGenerateResponse:
    """Generate promotional image using Hugging Face Inference API."""
    
    correlation_id = get_correlation_id()
    
    try:
        # Validate prompt
        if not prompt_brief.strip():
            raise ValidationError("Prompt brief cannot be empty", correlation_id)
            
        # Validate aspect ratio
        supported_ratios = ["1:1", "16:9", "9:16", "4:3", "3:4"]
        if aspect_ratio not in supported_ratios:
            raise ValidationError(
                f"Unsupported aspect ratio: {aspect_ratio}. Supported: {', '.join(supported_ratios)}", 
                correlation_id
            )
        
        # Handle reference image if provided (for future use)
        if reference_image:
            logger.info(f"📷 Reference image uploaded: {reference_image.filename} ({reference_image.size} bytes)")
            # Note: Reference image handling can be implemented in future iterations
            # For now, we'll just log it but not use it in generation
        
        # Create request object
        request = ImageGenerateRequest(
            prompt_brief=prompt_brief,
            brand_style=brand_style,
            aspect_ratio=aspect_ratio,
            seed=seed
        )
        
        logger.info(f"🎨 Generating image: '{prompt_brief[:50]}...' ({aspect_ratio})")
        
        # Generate image
        result = await service.generate_image(request)
        
        logger.info(f"✨ Image generated successfully: {result.job_id}")
        return result
        
    except ValidationError:
        raise
    except ValueError as e:
        raise ServiceError(str(e), correlation_id)
    except Exception as e:
        logger.error(f"💥 Unexpected error generating image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/health")
async def images_health_check(
    service: ImagesService = Depends(get_images_service),
) -> dict:
    """Check health of image generation services."""
    
    try:
        health_status = await service.health_check()
        
        # Return appropriate status code
        if health_status["status"] == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_status
            )
        elif health_status["status"] == "degraded":
            logger.warning("⚠️ Image services are degraded")
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "unhealthy", "error": str(e)}
        )


@router.get("/artifacts/{job_id}")
async def get_artifact_info(
    job_id: str,
    service: ImagesService = Depends(get_images_service),
) -> dict:
    """Get information about generated artifacts."""
    
    if not job_id.strip():
        raise ValidationError("Job ID cannot be empty", get_correlation_id())
    
    artifact_info = service.get_artifact_info(job_id)
    
    if not artifact_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifacts not found for job ID: {job_id}"
        )
    
    return artifact_info


@router.get("/artifacts/{job_id}/download/{filename}")
async def download_artifact(
    job_id: str,
    filename: str,
    service: ImagesService = Depends(get_images_service),
) -> FileResponse:
    """Download a specific artifact file."""
    
    from ...infra.storage import storage
    
    if not job_id.strip() or not filename.strip():
        raise ValidationError("Job ID and filename cannot be empty", get_correlation_id())
    
    # Get file path
    file_path = storage.get_artifact_path(job_id, filename)
    
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename} for job {job_id}"
        )
    
    # Determine media type
    media_type = "application/octet-stream"
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        media_type = "image/png" if filename.lower().endswith('.png') else "image/jpeg"
    elif filename.lower().endswith('.json'):
        media_type = "application/json"
    
    logger.info(f"📥 Serving artifact: {job_id}/{filename}")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@router.post("/regenerate/{job_id}", response_model=ImageGenerateResponse)
async def regenerate_image(
    job_id: str,
    prompt_brief: Optional[str] = Form(None, description="New prompt (optional)"),
    brand_style: Optional[str] = Form(None, description="New brand style (optional)"),
    aspect_ratio: Optional[str] = Form(None, description="New aspect ratio (optional)"),
    seed: Optional[int] = Form(None, description="New seed (optional)"),
    service: ImagesService = Depends(get_images_service),
) -> ImageGenerateResponse:
    """Regenerate image with optional modifications."""
    
    correlation_id = get_correlation_id()
    
    if not job_id.strip():
        raise ValidationError("Job ID cannot be empty", correlation_id)
    
    # Collect modifications
    modifications = {}
    if prompt_brief:
        modifications["prompt_brief"] = prompt_brief
    if brand_style:
        modifications["brand_style"] = brand_style
    if aspect_ratio:
        modifications["aspect_ratio"] = aspect_ratio
    if seed is not None:
        modifications["seed"] = seed
    
    try:
        logger.info(f"🔄 Regenerating image {job_id} with {len(modifications)} modifications")
        
        result = await service.regenerate_image(job_id, modifications)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot regenerate: job {job_id} not found or invalid"
            )
        
        logger.info(f"✨ Image regenerated successfully: {result.job_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Regeneration failed for {job_id}: {e}")
        raise ServiceError(f"Regeneration failed: {e}", correlation_id)