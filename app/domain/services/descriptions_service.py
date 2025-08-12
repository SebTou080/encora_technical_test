"""Service layer for descriptions generation."""

from typing import Dict, List

from ...core.logging import get_logger
from ..chains.descriptions_chain import DescriptionsChain
from ..models.descriptions import DescriptionGenerateRequest, DescriptionGenerateResponse

logger = get_logger(__name__)


class DescriptionsService:
    """Service for orchestrating descriptions generation."""

    def __init__(self) -> None:
        """Initialize the descriptions service."""
        self.chain = DescriptionsChain()

    async def generate_descriptions(self, request: DescriptionGenerateRequest) -> DescriptionGenerateResponse:
        """Generate product descriptions for specified channels."""
        logger.info(f"🎯 Starting generation for {request.product_name}")
        
        try:
            # Validate channels
            supported_channels = {"ecommerce", "mercado_libre", "instagram"}
            invalid_channels = set(request.channels) - supported_channels
            if invalid_channels:
                raise ValueError(f"Unsupported channels: {invalid_channels}")

            # Generate descriptions
            result = await self.chain.generate(request)
            
            logger.info(f"🎉 Successfully generated descriptions for {request.product_name}")
            return result

        except Exception as e:
            logger.error(f"💥 Generation failed for {request.product_name}: {e}")
            raise

