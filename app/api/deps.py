"""Dependency injection for FastAPI routes."""

from typing import Generator

from ..domain.services.descriptions_service import DescriptionsService
from ..domain.services.images_service import ImagesService


def get_descriptions_service() -> Generator[DescriptionsService, None, None]:
    """Get descriptions service instance."""
    service = DescriptionsService()
    try:
        yield service
    finally:
        # Cleanup if needed
        pass


def get_images_service() -> Generator[ImagesService, None, None]:
    """Get images service instance."""
    service = ImagesService()
    try:
        yield service
    finally:
        # Cleanup if needed
        pass