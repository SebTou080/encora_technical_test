"""Dependency injection for FastAPI routes."""

from typing import Generator

from ..domain.services.descriptions_service import DescriptionsService


def get_descriptions_service() -> Generator[DescriptionsService, None, None]:
    """Get descriptions service instance."""
    service = DescriptionsService()
    try:
        yield service
    finally:
        # Cleanup if needed
        pass