"""Description request and response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .product import NutritionFacts


class SEOMetadata(BaseModel):
    """SEO metadata for descriptions."""
    keywords: List[str] = Field(default_factory=list, description="SEO keywords")
    meta_title: Optional[str] = Field(None, description="Meta title")
    meta_description: Optional[str] = Field(None, description="Meta description")


class EcommerceDescription(BaseModel):
    """E-commerce platform description."""
    title: str = Field(..., description="Product title")
    short_description: str = Field(..., description="Brief description")
    long_description: str = Field(..., description="Detailed description")
    bullets: List[str] = Field(..., description="Key points as bullets")
    seo: SEOMetadata = Field(..., description="SEO metadata")


class MercadoLibreDescription(BaseModel):
    """MercadoLibre platform description."""
    title: str = Field(..., description="Product title")
    bullets: List[str] = Field(..., description="Key features as bullets")


class InstagramDescription(BaseModel):
    """Instagram post description."""
    caption: str = Field(..., description="Post caption")
    hashtags: List[str] = Field(..., description="Relevant hashtags")


class ComplianceInfo(BaseModel):
    """Compliance and regulatory information."""
    health_claims: List[str] = Field(default_factory=list, description="Health claims made")
    reading_level: str = Field("B1", description="Estimated reading level")


class TraceInfo(BaseModel):
    """Generation trace information."""
    model: str = Field(..., description="Model used")
    input_tokens: int = Field(0, description="Input tokens consumed")
    output_tokens: int = Field(0, description="Output tokens generated")


class DescriptionGenerateRequest(BaseModel):
    """Request for generating product descriptions."""
    product_name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Stock keeping unit")
    brand: str = Field(..., description="Brand name")
    language: str = Field("es", description="Output language")
    channels: List[str] = Field(..., description="Target channels")
    target_audience: Optional[str] = Field(None, description="Target audience")
    category: str = Field(..., description="Product category")
    features: List[str] = Field(default_factory=list, description="Key features")
    ingredients: List[str] = Field(default_factory=list, description="Main ingredients")
    nutrition_facts: Optional[NutritionFacts] = Field(None, description="Nutrition information")
    tone: str = Field("cálido y experto", description="Brand tone")
    variants: int = Field(1, description="Number of variants to generate")


class DescriptionGenerateResponse(BaseModel):
    """Response from description generation."""
    sku: str = Field(..., description="Stock keeping unit")
    language: str = Field(..., description="Output language")
    by_channel: Dict[str, Any] = Field(..., description="Descriptions by channel")
    compliance: ComplianceInfo = Field(..., description="Compliance information")
    trace: TraceInfo = Field(..., description="Generation trace")