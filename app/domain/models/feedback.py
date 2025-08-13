"""Feedback analysis request and response models."""

from typing import Any

from pydantic import BaseModel, Field


class SentimentScore(BaseModel):
    """Sentiment analysis result."""

    label: str = Field(..., description="Sentiment label (positive/neutral/negative)")
    score: float = Field(..., description="Confidence score (0.0-1.0)")


class Theme(BaseModel):
    """Identified theme in feedback."""

    name: str = Field(..., description="Theme name")
    examples: list[str] = Field(..., description="Example comments")


class Issue(BaseModel):
    """Identified issue from feedback."""

    issue: str = Field(..., description="Issue description")
    count: int = Field(..., description="Number of occurrences")
    priority: str = Field(..., description="Priority level (alta/media/baja)")


class FeatureRequest(BaseModel):
    """Feature request from feedback."""

    request: str = Field(..., description="Feature request description")
    count: int = Field(..., description="Number of requests")


class Highlight(BaseModel):
    """Notable feedback highlight."""

    quote: str = Field(..., description="Notable quote")
    channel: str | None = Field(None, description="Source channel")


class FeedbackAnalyzeResponse(BaseModel):
    """Response from feedback analysis."""

    overall_sentiment: SentimentScore = Field(..., description="Overall sentiment")
    themes: list[Theme] = Field(..., description="Identified themes")
    top_issues: list[Issue] = Field(..., description="Top issues by priority")
    feature_requests: list[FeatureRequest] = Field(..., description="Feature requests")
    highlights: list[Highlight] = Field(..., description="Notable quotes")
    by_channel: dict[str, Any] = Field(
        default_factory=dict, description="Analysis by channel"
    )
