"""Centralized error handling for the API."""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    message: str
    correlation_id: Optional[str] = None


class ValidationError(HTTPException):
    """Custom validation error."""
    
    def __init__(self, message: str, correlation_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                error="validation_error",
                message=message,
                correlation_id=correlation_id
            ).model_dump()
        )


class ServiceError(HTTPException):
    """Custom service error."""
    
    def __init__(self, message: str, correlation_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="service_error",
                message=message,
                correlation_id=correlation_id
            ).model_dump()
        )