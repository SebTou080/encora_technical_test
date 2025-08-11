"""FastAPI application main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.middleware import CorrelationIdMiddleware
from .api.routers import descriptions, images
from .core.config import settings
from .core.logging import setup_logging

# Set up logging
setup_logging()

# Create FastAPI application
app = FastAPI(
    title="Healthy Snack IA",
    description="AI-powered snack marketing content generator",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(descriptions.router)
app.include_router(images.router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )