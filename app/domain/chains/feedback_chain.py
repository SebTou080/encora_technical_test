"""Feedback analysis chain using LangChain for sentiment analysis and insights extraction."""

import asyncio
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...core.config import settings
from ...core.logging import get_logger
from ..models.feedback import (
    FeedbackAnalyzeResponse,
    FeatureRequest,
    Highlight,
    Issue,
    SentimentScore,
    Theme,
)

logger = get_logger(__name__)


class CommentAnalysis(BaseModel):
    """Individual comment analysis result."""
    sentiment: str = Field(..., description="Sentiment: positive, neutral, or negative")
    sentiment_score: float = Field(..., description="Confidence score (0.0-1.0)")
    themes: List[str] = Field(..., description="Main themes (max 3)")
    issues: List[str] = Field(default_factory=list, description="Issues mentioned")
    issue_priority: Optional[str] = Field(None, description="Priority: alta, media, baja")
    feature_requests: List[str] = Field(default_factory=list, description="Feature requests")


class FeedbackChain:
    """Chain for analyzing feedback comments using LLM."""

    def __init__(self) -> None:
        """Initialize the feedback chain."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,  # Lower temperature for more consistent analysis
            timeout=settings.request_timeout_s,
            max_retries=1,
            request_timeout=30,
        )
        self.parser = PydanticOutputParser(pydantic_object=CommentAnalysis)
        self.prompt = self._create_analysis_prompt()
        self.chain = self.prompt | self.llm | self.parser
        self.insights_guidelines = self._load_insights_guidelines()

    def _load_insights_guidelines(self) -> str:
        """Load insights analysis guidelines."""
        try:
            guidelines_path = Path(__file__).parent.parent / "prompts" / "system_insights.md"
            return guidelines_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"❌ Failed to load insights guidelines: {e}")
            return "Analyze feedback for sentiment, themes, issues, and feature requests."

    def _create_analysis_prompt(self) -> PromptTemplate:
        """Create the analysis prompt template."""
        template = """
Eres un experto analista de feedback de productos de snacks saludables.

CONTEXTO Y DIRECTRICES:
{guidelines}

TAREA:
Analiza el siguiente comentario de usuario y extrae:
1. Sentimiento (positive/neutral/negative) con score de confianza
2. Temas principales mencionados (máximo 3)
3. Issues o problemas identificados con prioridad
4. Feature requests o sugerencias

COMENTARIO A ANALIZAR:
"{comment}"

INFORMACIÓN ADICIONAL:
- SKU: {sku}
- Canal: {channel}
- Usuario: {username}

IMPORTANTE:
- Sé preciso y consistente en la clasificación
- Considera el contexto de snacks saludables
- Identifica tanto aspectos positivos como negativos
- Si no hay issues o requests, deja las listas vacías

{format_instructions}
"""
        return PromptTemplate(
            template=template,
            input_variables=["comment", "sku", "channel", "username", "guidelines"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

    async def analyze_comment(
        self, 
        comment: str, 
        username: str = "anonymous",
        sku: Optional[str] = None,
        channel: Optional[str] = None
    ) -> CommentAnalysis:
        """Analyze a single comment."""
        
        try:
            input_data = {
                "comment": comment.strip(),
                "username": username,
                "sku": sku or "unknown",
                "channel": channel or "unknown",
                "guidelines": self.insights_guidelines[:1500]  # Limit guidelines length
            }

            logger.info(f"🧠 Analyzing comment from {username}: '{comment[:50]}...'")
            result = await self.chain.ainvoke(input_data)
            
            # Validate and clean results
            result = self._validate_analysis(result)
            
            logger.info(f"✨ Analysis complete: {result.sentiment} ({result.sentiment_score:.2f})")
            return result

        except Exception as e:
            logger.error(f"💥 Comment analysis failed for {username}: {e}")
            # Return fallback analysis
            return CommentAnalysis(
                sentiment="neutral",
                sentiment_score=0.5,
                themes=["general"],
                issues=[],
                issue_priority=None,
                feature_requests=[]
            )

    def _validate_analysis(self, analysis: CommentAnalysis) -> CommentAnalysis:
        """Validate and clean analysis results."""
        # Ensure sentiment is valid
        if analysis.sentiment not in ["positive", "neutral", "negative"]:
            analysis.sentiment = "neutral"
        
        # Ensure score is in valid range
        analysis.sentiment_score = max(0.0, min(1.0, analysis.sentiment_score))
        
        # Limit themes to max 3
        analysis.themes = analysis.themes[:3] if analysis.themes else ["general"]
        
        # Clean and limit issues
        analysis.issues = [issue.lower().strip() for issue in analysis.issues if issue.strip()][:3]
        
        # Validate priority
        if analysis.issue_priority and analysis.issue_priority not in ["alta", "media", "baja"]:
            analysis.issue_priority = "media" if analysis.issues else None
        
        # Clean feature requests
        analysis.feature_requests = [req.strip() for req in analysis.feature_requests if req.strip()][:3]
        
        return analysis

    async def analyze_batch(
        self,
        comments_data: List[Dict[str, Any]],
        max_concurrency: int = None
    ) -> List[CommentAnalysis]:
        """Analyze a batch of comments concurrently."""
        
        if not comments_data:
            return []

        max_concurrency = max_concurrency or settings.max_concurrency
        semaphore = asyncio.Semaphore(max_concurrency)
        
        logger.info(f"🚀 Starting batch analysis of {len(comments_data)} comments (concurrency: {max_concurrency})")

        async def analyze_single(comment_data: Dict[str, Any]) -> CommentAnalysis:
            async with semaphore:
                return await self.analyze_comment(
                    comment=comment_data.get("comment", ""),
                    username=comment_data.get("username", "anonymous"),
                    sku=comment_data.get("sku"),
                    channel=comment_data.get("channel")
                )

        # Process all comments concurrently
        tasks = [analyze_single(comment_data) for comment_data in comments_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        valid_results = []
        error_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Analysis failed for comment {i}: {result}")
                error_count += 1
                # Add fallback result
                valid_results.append(CommentAnalysis(
                    sentiment="neutral",
                    sentiment_score=0.5,
                    themes=["error"],
                    issues=[],
                    feature_requests=[]
                ))
            else:
                valid_results.append(result)

        logger.info(f"✨ Batch analysis complete: {len(valid_results)} processed, {error_count} errors")
        return valid_results

    def aggregate_results(
        self, 
        analyses: List[CommentAnalysis],
        comments_data: List[Dict[str, Any]]
    ) -> FeedbackAnalyzeResponse:
        """Aggregate individual analyses into final response."""
        
        if not analyses:
            logger.warning("⚠️ No analyses to aggregate")
            return FeedbackAnalyzeResponse(
                overall_sentiment=SentimentScore(label="neutral", score=0.5),
                themes=[],
                top_issues=[],
                feature_requests=[],
                highlights=[],
                by_sku={},
                by_channel={}
            )

        logger.info(f"📊 Aggregating results from {len(analyses)} analyses")

        # Calculate overall sentiment
        sentiment_counts = Counter(a.sentiment for a in analyses)
        sentiment_scores = [a.sentiment_score for a in analyses if a.sentiment_score > 0]
        
        overall_sentiment_label = sentiment_counts.most_common(1)[0][0]
        overall_sentiment_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5

        # Aggregate themes
        theme_counter = Counter()
        for analysis in analyses:
            theme_counter.update(analysis.themes)
        
        themes = [
            Theme(name=theme, examples=self._get_theme_examples(theme, analyses, comments_data))
            for theme, count in theme_counter.most_common(10)
        ]

        # Aggregate issues
        issue_counter = Counter()
        issue_priorities = {}
        
        for analysis in analyses:
            for issue in analysis.issues:
                issue_counter[issue] += 1
                if analysis.issue_priority:
                    issue_priorities[issue] = analysis.issue_priority

        top_issues = [
            Issue(
                issue=issue,
                count=count,
                priority=issue_priorities.get(issue, "media")
            )
            for issue, count in issue_counter.most_common(10)
        ]

        # Aggregate feature requests
        request_counter = Counter()
        for analysis in analyses:
            request_counter.update(analysis.feature_requests)

        feature_requests = [
            FeatureRequest(request=request, count=count)
            for request, count in request_counter.most_common(10)
        ]

        # Generate highlights
        highlights = self._generate_highlights(analyses, comments_data)

        # Aggregate by SKU and channel
        by_sku = self._aggregate_by_field(analyses, comments_data, "sku")
        by_channel = self._aggregate_by_field(analyses, comments_data, "channel")

        logger.info(f"✅ Aggregation complete: {len(themes)} themes, {len(top_issues)} issues, {len(feature_requests)} requests")

        return FeedbackAnalyzeResponse(
            overall_sentiment=SentimentScore(label=overall_sentiment_label, score=overall_sentiment_score),
            themes=themes,
            top_issues=top_issues,
            feature_requests=feature_requests,
            highlights=highlights,
            by_sku=by_sku,
            by_channel=by_channel
        )

    def _get_theme_examples(
        self, 
        theme: str, 
        analyses: List[CommentAnalysis], 
        comments_data: List[Dict[str, Any]]
    ) -> List[str]:
        """Get example comments for a theme."""
        examples = []
        for i, analysis in enumerate(analyses):
            if theme in analysis.themes and i < len(comments_data):
                comment = comments_data[i].get("comment", "")
                if comment and len(comment) < 100:  # Short comments only
                    examples.append(comment)
                if len(examples) >= 3:  # Limit to 3 examples
                    break
        return examples

    def _generate_highlights(
        self, 
        analyses: List[CommentAnalysis], 
        comments_data: List[Dict[str, Any]]
    ) -> List[Highlight]:
        """Generate notable highlights from comments."""
        highlights = []
        
        # Get highly positive comments
        for i, analysis in enumerate(analyses):
            if (analysis.sentiment == "positive" and 
                analysis.sentiment_score > 0.8 and 
                i < len(comments_data)):
                
                comment_data = comments_data[i]
                comment = comment_data.get("comment", "")
                
                if len(comment) > 20 and len(comment) < 150:  # Good length for highlights
                    highlights.append(Highlight(
                        quote=comment,
                        sku=comment_data.get("sku"),
                        channel=comment_data.get("channel")
                    ))
                    
                if len(highlights) >= 5:  # Limit highlights
                    break
        
        return highlights

    def _aggregate_by_field(
        self, 
        analyses: List[CommentAnalysis], 
        comments_data: List[Dict[str, Any]], 
        field: str
    ) -> Dict[str, Any]:
        """Aggregate results by a specific field (sku or channel)."""
        field_data = defaultdict(lambda: {
            "sentiments": Counter(),
            "themes": Counter(),
            "issues": Counter(),
            "total_comments": 0
        })
        
        for i, analysis in enumerate(analyses):
            if i < len(comments_data):
                field_value = comments_data[i].get(field, "unknown")
                data = field_data[field_value]
                
                data["sentiments"][analysis.sentiment] += 1
                data["themes"].update(analysis.themes)
                data["issues"].update(analysis.issues)
                data["total_comments"] += 1
        
        # Convert to final format
        result = {}
        for field_value, data in field_data.items():
            if data["total_comments"] > 0:
                result[field_value] = {
                    "total_comments": data["total_comments"],
                    "sentiment_distribution": dict(data["sentiments"]),
                    "top_themes": [theme for theme, _ in data["themes"].most_common(5)],
                    "top_issues": [issue for issue, _ in data["issues"].most_common(3)]
                }
        
        return result