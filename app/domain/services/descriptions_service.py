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
        logger.info(f"🎯 Starting generation for {request.sku}")
        
        try:
            # Validate channels
            supported_channels = {"ecommerce", "mercado_libre", "instagram"}
            invalid_channels = set(request.channels) - supported_channels
            if invalid_channels:
                raise ValueError(f"Unsupported channels: {invalid_channels}")

            # Generate descriptions
            result = await self.chain.generate(request)
            
            logger.info(f"🎉 Successfully generated descriptions for {request.sku}")
            return result

        except Exception as e:
            logger.error(f"💥 Generation failed for {request.sku}: {e}")
            raise

    async def generate_variants(
        self, 
        request: DescriptionGenerateRequest
    ) -> List[DescriptionGenerateResponse]:
        """Generate multiple variants of descriptions concurrently."""
        import asyncio
        
        logger.info(f"🚀 Launching {request.variants} concurrent tasks for {request.sku}")
        
        # Generate all variants concurrently
        tasks = []
        for i in range(request.variants):
            task = self.generate_descriptions(request)
            tasks.append(task)
        
        # Wait for all variants to complete
        variants = await asyncio.gather(*tasks)
        
        logger.info(f"🏆 All {len(variants)} variants completed for {request.sku}")
        return variants