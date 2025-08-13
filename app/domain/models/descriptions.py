"""Description request and response models."""

from typing import Any

from pydantic import BaseModel, Field

from .product import NutritionFacts


class SEOMetadata(BaseModel):
    """SEO metadata for descriptions."""

    keywords: list[str] = Field(default_factory=list, description="SEO keywords")
    meta_title: str | None = Field(None, description="Meta title")
    meta_description: str | None = Field(None, description="Meta description")


class EcommerceDescription(BaseModel):
    """E-commerce platform description."""

    title: str = Field(..., description="Product title")
    short_description: str = Field(..., description="Brief description")
    long_description: str = Field(..., description="Detailed description")
    bullets: list[str] = Field(..., description="Key points as bullets")
    seo: SEOMetadata = Field(..., description="SEO metadata")


class MercadoLibreDescription(BaseModel):
    """MercadoLibre platform description."""

    title: str = Field(..., description="Product title")
    bullets: list[str] = Field(..., description="Key features as bullets")


class InstagramDescription(BaseModel):
    """Instagram post description."""

    caption: str = Field(..., description="Post caption")
    hashtags: list[str] = Field(..., description="Relevant hashtags")


class ComplianceInfo(BaseModel):
    """Compliance and regulatory information."""

    health_claims: list[str] = Field(
        default_factory=list, description="Health claims made"
    )
    reading_level: str = Field("B1", description="Estimated reading level")


class TraceInfo(BaseModel):
    """Generation trace information."""

    model: str = Field(..., description="Model used")
    input_tokens: int = Field(0, description="Input tokens consumed")
    output_tokens: int = Field(0, description="Output tokens generated")


class DescriptionGenerateRequest(BaseModel):
    """Request for generating product descriptions."""

    product_name: str = Field(..., description="Product name")
    brand: str = Field(..., description="Brand name")
    channels: list[str] = Field(..., description="Target channels")
    target_audience: str | None = Field(None, description="Target audience")
    category: str = Field(..., description="Product category")
    features: list[str] = Field(default_factory=list, description="Key features")
    ingredients: list[str] = Field(default_factory=list, description="Main ingredients")
    nutrition_facts: NutritionFacts | None = Field(
        None, description="Nutrition information"
    )
    tone: str = Field("cálido y experto", description="Brand tone")


class DescriptionGenerateResponse(BaseModel):
    """Response from description generation."""

    product_name: str = Field(..., description="Product name")
    brand: str = Field(..., description="Brand name")
    by_channel: dict[str, Any] = Field(..., description="Descriptions by channel")
    compliance: ComplianceInfo = Field(..., description="Compliance information")
    trace: TraceInfo = Field(..., description="Generation trace")
