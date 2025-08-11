"""Product domain models."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class NutritionFacts(BaseModel):
    """Nutrition facts per serving."""
    calories: Optional[int] = Field(None, description="Calories per serving")
    protein_g: Optional[float] = Field(None, description="Protein in grams")
    fat_g: Optional[float] = Field(None, description="Fat in grams")
    carbs_g: Optional[float] = Field(None, description="Carbohydrates in grams")
    fiber_g: Optional[float] = Field(None, description="Fiber in grams")
    sugar_g: Optional[float] = Field(None, description="Sugar in grams")
    sodium_mg: Optional[float] = Field(None, description="Sodium in milligrams")


class ProductBrief(BaseModel):
    """Basic product information."""
    product_name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Stock keeping unit")
    brand: str = Field(..., description="Brand name")
    category: str = Field(..., description="Product category")
    features: List[str] = Field(default_factory=list, description="Key features")
    ingredients: List[str] = Field(default_factory=list, description="Main ingredients")
    nutrition_facts: Optional[NutritionFacts] = Field(None, description="Nutrition information")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    tone: Optional[str] = Field("friendly", description="Brand tone")