"""Descriptions API router."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ...core.logging import get_correlation_id, get_logger
from ...domain.models.descriptions import (
    DescriptionGenerateRequest,
    DescriptionGenerateResponse,
)
from ...domain.services.descriptions_service import DescriptionsService
from ..deps import get_descriptions_service
from ..errors import ServiceError, ValidationError

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/descriptions", tags=["descriptions"])


@router.post("/generate", response_model=DescriptionGenerateResponse)
async def generate_descriptions(
    request: DescriptionGenerateRequest,
    service: DescriptionsService = Depends(get_descriptions_service),
) -> DescriptionGenerateResponse:
    """Generate product descriptions for specified channels."""
    correlation_id = get_correlation_id()
    
    try:
        # Validate request
        if not request.channels:
            raise ValidationError("At least one channel must be specified", correlation_id)
        
        if not request.product_name.strip():
            raise ValidationError("Product name cannot be empty", correlation_id)
            
        if not request.sku.strip():
            raise ValidationError("SKU cannot be empty", correlation_id)
        
        # Generate descriptions
        channels_str = ", ".join(request.channels)
        logger.info(f"📝 Generating content for '{request.product_name}' → {channels_str} (variants: {request.variants})")
        
        if request.variants > 1:
            logger.info(f"🔄 Processing {request.variants} variants concurrently...")
            variants = await service.generate_variants(request)
            logger.info(f"✨ Generated {len(variants)} variants successfully")
            return variants[0] if variants else None
        else:
            return await service.generate_descriptions(request)
            
    except ValidationError:
        raise
    except ValueError as e:
        raise ServiceError(str(e), correlation_id)
    except Exception as e:
        logger.error(f"Unexpected error generating descriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )