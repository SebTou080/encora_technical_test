"""Middleware for correlation ID and logging."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging import generate_correlation_id, get_logger, set_correlation_id

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation ID and request logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID."""
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Request-Id") or generate_correlation_id()
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Log request start
        start_time = time.time()
        logger.info(f"🚀 Incoming {request.method} {request.url.path}")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Log request completion
            duration = time.time() - start_time
            if response.status_code < 400:
                logger.info(f"✅ Completed {request.method} {request.url.path} - {response.status_code} ({duration:.2f}s)")
            else:
                logger.warning(f"⚠️ Completed {request.method} {request.url.path} - {response.status_code} ({duration:.2f}s)")
            
            # Add correlation ID to response headers
            response.headers["X-Request-Id"] = correlation_id
            
            return response
            
        except Exception as e:
            # Log request error
            duration = time.time() - start_time
            logger.error(f"❌ Failed {request.method} {request.url.path} - {str(e)} ({duration:.2f}s)")
            raise