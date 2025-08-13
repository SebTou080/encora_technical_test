"""Product domain models."""

from pydantic import BaseModel, Field


class NutritionFacts(BaseModel):
    """Nutrition facts per serving."""

    calories: int | None = Field(None, description="Calories per serving")
    protein_g: float | None = Field(None, description="Protein in grams")
    fat_g: float | None = Field(None, description="Fat in grams")
    carbs_g: float | None = Field(None, description="Carbohydrates in grams")
