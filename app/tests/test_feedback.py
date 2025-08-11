"""Tests for feedback analysis functionality."""

import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi import UploadFile

from ..domain.chains.feedback_chain import CommentAnalysis, FeedbackChain
from ..domain.models.feedback import (
    FeedbackAnalyzeResponse,
    FeatureRequest,
    Highlight,
    Issue,
    SentimentScore,
    Theme,
)
from ..domain.services.feedback_service import FeedbackService


@pytest.fixture
def sample_comments_data():
    """Sample comments data for testing."""
    return [
        {
            "comment": "Me encantan estos chips de kale, muy crujientes y saludables",
            "username": "user123",
            "sku": "KALE-90G",
            "channel": "ecommerce"
        },
        {
            "comment": "El sabor podría ser mejor, pero la textura está bien",
            "username": "user456",
            "sku": "KALE-90G",
            "channel": "instagram"
        },
        {
            "comment": "Horrible, muy caro para lo que es. No lo recomiendo",
            "username": "user789",
            "sku": "QUINOA-80G",
            "channel": "mercadolibre"
        },
        {
            "comment": "¿Podrían hacer una versión sin sal? Sería perfecto",
            "username": "user101",
            "sku": "KALE-90G", 
            "channel": "instagram"
        },
        {
            "comment": "Excelente producto, lo compro siempre. Felicitaciones",
            "username": "user202",
            "sku": "QUINOA-80G",
            "channel": "ecommerce"
        }
    ]


@pytest.fixture
def sample_csv_content():
    """Sample CSV file content."""
    csv_data = """comment,username,sku,channel
"Me encantan estos chips de kale, muy crujientes",user123,KALE-90G,ecommerce
"El sabor podría ser mejor",user456,KALE-90G,instagram
"Horrible, muy caro",user789,QUINOA-80G,mercadolibre
"¿Versión sin sal?",user101,KALE-90G,instagram
"Excelente producto",user202,QUINOA-80G,ecommerce"""
    return csv_data.encode('utf-8')


@pytest.fixture
def sample_excel_content():
    """Sample Excel file content."""
    df = pd.DataFrame([
        {"comment": "Me encantan estos chips", "username": "user1", "sku": "KALE-90G", "channel": "web"},
        {"comment": "Sabor regular", "username": "user2", "sku": "QUINOA-80G", "channel": "app"},
        {"comment": "Muy caros", "username": "user3", "sku": "KALE-90G", "channel": "web"}
    ])
    
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture 
def mock_comment_analysis():
    """Mock comment analysis results."""
    return [
        CommentAnalysis(
            sentiment="positive",
            sentiment_score=0.9,
            themes=["sabor", "textura"],
            issues=[],
            issue_priority=None,
            feature_requests=[]
        ),
        CommentAnalysis(
            sentiment="neutral", 
            sentiment_score=0.6,
            themes=["sabor", "textura"],
            issues=["sabor"],
            issue_priority="media",
            feature_requests=[]
        ),
        CommentAnalysis(
            sentiment="negative",
            sentiment_score=0.2, 
            themes=["precio"],
            issues=["precio"],
            issue_priority="alta",
            feature_requests=[]
        ),
        CommentAnalysis(
            sentiment="neutral",
            sentiment_score=0.7,
            themes=["variedad"],
            issues=[],
            issue_priority=None,
            feature_requests=["version_sin_sal"]
        ),
        CommentAnalysis(
            sentiment="positive",
            sentiment_score=0.8,
            themes=["calidad"],
            issues=[],
            issue_priority=None,
            feature_requests=[]
        )
    ]


class TestCommentAnalysis:
    """Test comment analysis model validation."""
    
    def test_comment_analysis_validation(self):
        """Test CommentAnalysis model validation."""
        analysis = CommentAnalysis(
            sentiment="positive",
            sentiment_score=0.8,
            themes=["sabor", "textura"],
            issues=[],
            feature_requests=[]
        )
        
        assert analysis.sentiment == "positive"
        assert analysis.sentiment_score == 0.8
        assert len(analysis.themes) == 2
        assert analysis.issues == []
        assert analysis.feature_requests == []

    def test_comment_analysis_invalid_sentiment(self):
        """Test validation with invalid sentiment."""
        # This should be handled by the validation in the chain
        analysis = CommentAnalysis(
            sentiment="invalid",
            sentiment_score=0.8,
            themes=["sabor"],
            issues=[],
            feature_requests=[]
        )
        # The model allows it, validation happens in the chain
        assert analysis.sentiment == "invalid"


class TestFeedbackChain:
    """Test feedback analysis chain functionality."""
    
    @patch('langchain_openai.ChatOpenAI')
    async def test_analyze_comment(self, mock_llm_class):
        """Test single comment analysis."""
        # Mock LLM response
        mock_llm = AsyncMock()
        mock_analysis = CommentAnalysis(
            sentiment="positive",
            sentiment_score=0.9,
            themes=["sabor", "calidad"],
            issues=[],
            feature_requests=[]
        )
        
        # Mock the chain
        chain = FeedbackChain()
        chain.chain = AsyncMock(return_value=mock_analysis)
        
        result = await chain.analyze_comment(
            comment="Me encanta este producto",
            username="testuser",
            sku="TEST-001",
            channel="web"
        )
        
        assert isinstance(result, CommentAnalysis)
        assert result.sentiment == "positive"
        assert result.sentiment_score == 0.9
        assert "sabor" in result.themes

    def test_validate_analysis(self):
        """Test analysis validation and cleaning."""
        chain = FeedbackChain()
        
        # Test with invalid data
        invalid_analysis = CommentAnalysis(
            sentiment="invalid_sentiment",
            sentiment_score=1.5,  # Out of range
            themes=["theme1", "theme2", "theme3", "theme4"],  # Too many
            issues=["issue1", "issue2", "issue3", "issue4"],  # Too many
            issue_priority="invalid_priority",
            feature_requests=["req1", "req2", "req3", "req4"]  # Too many
        )
        
        validated = chain._validate_analysis(invalid_analysis)
        
        assert validated.sentiment == "neutral"  # Corrected
        assert validated.sentiment_score == 1.0  # Clamped
        assert len(validated.themes) <= 3  # Limited
        assert len(validated.issues) <= 3  # Limited
        assert validated.issue_priority in ["alta", "media", "baja"] or validated.issue_priority is None
        assert len(validated.feature_requests) <= 3  # Limited

    @patch.object(FeedbackChain, 'analyze_comment')
    async def test_analyze_batch_concurrency(self, mock_analyze, sample_comments_data):
        """Test concurrent batch analysis."""
        # Mock individual analysis calls
        mock_analyze.side_effect = [
            CommentAnalysis(sentiment="positive", sentiment_score=0.8, themes=["sabor"], issues=[], feature_requests=[]),
            CommentAnalysis(sentiment="neutral", sentiment_score=0.6, themes=["textura"], issues=["sabor"], feature_requests=[]),
            CommentAnalysis(sentiment="negative", sentiment_score=0.3, themes=["precio"], issues=["precio"], feature_requests=[]),
            CommentAnalysis(sentiment="neutral", sentiment_score=0.7, themes=["variedad"], issues=[], feature_requests=["sin_sal"]),
            CommentAnalysis(sentiment="positive", sentiment_score=0.9, themes=["calidad"], issues=[], feature_requests=[])
        ]
        
        chain = FeedbackChain()
        results = await chain.analyze_batch(sample_comments_data, max_concurrency=2)
        
        assert len(results) == 5
        assert mock_analyze.call_count == 5
        
        # Verify different sentiments were returned
        sentiments = [r.sentiment for r in results]
        assert "positive" in sentiments
        assert "negative" in sentiments
        assert "neutral" in sentiments

    def test_aggregate_results(self, mock_comment_analysis, sample_comments_data):
        """Test results aggregation."""
        chain = FeedbackChain()
        
        result = chain.aggregate_results(mock_comment_analysis, sample_comments_data)
        
        assert isinstance(result, FeedbackAnalyzeResponse)
        assert isinstance(result.overall_sentiment, SentimentScore)
        assert result.overall_sentiment.label in ["positive", "neutral", "negative"]
        assert 0.0 <= result.overall_sentiment.score <= 1.0
        
        # Check themes
        assert len(result.themes) > 0
        assert all(isinstance(theme, Theme) for theme in result.themes)
        
        # Check issues
        assert len(result.top_issues) > 0
        assert all(isinstance(issue, Issue) for issue in result.top_issues)
        
        # Check feature requests
        assert len(result.feature_requests) > 0
        assert all(isinstance(req, FeatureRequest) for req in result.feature_requests)
        
        # Check aggregations exist
        assert isinstance(result.by_sku, dict)
        assert isinstance(result.by_channel, dict)

    def test_aggregate_empty_results(self):
        """Test aggregation with empty results."""
        chain = FeedbackChain()
        
        result = chain.aggregate_results([], [])
        
        assert isinstance(result, FeedbackAnalyzeResponse)
        assert result.overall_sentiment.label == "neutral"
        assert result.overall_sentiment.score == 0.5
        assert len(result.themes) == 0
        assert len(result.top_issues) == 0
        assert len(result.feature_requests) == 0


class TestFeedbackService:
    """Test feedback service functionality."""

    def test_create_upload_file_csv(self, sample_csv_content):
        """Helper to create UploadFile for CSV."""
        return UploadFile(
            filename="test_feedback.csv",
            file=io.BytesIO(sample_csv_content)
        )

    def test_create_upload_file_excel(self, sample_excel_content):
        """Helper to create UploadFile for Excel."""
        return UploadFile(
            filename="test_feedback.xlsx", 
            file=io.BytesIO(sample_excel_content)
        )

    async def test_parse_csv_file(self, sample_csv_content):
        """Test CSV file parsing."""
        service = FeedbackService()
        
        upload_file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(sample_csv_content)
        )
        
        comments_data = await service._parse_feedback_file(upload_file)
        
        assert len(comments_data) == 5
        assert all("comment" in comment for comment in comments_data)
        assert all("username" in comment for comment in comments_data)
        
        # Check specific data
        first_comment = comments_data[0]
        assert "kale" in first_comment["comment"].lower()
        assert first_comment["sku"] == "KALE-90G"

    async def test_parse_excel_file(self, sample_excel_content):
        """Test Excel file parsing."""
        service = FeedbackService()
        
        upload_file = UploadFile(
            filename="test.xlsx",
            file=io.BytesIO(sample_excel_content)
        )
        
        comments_data = await service._parse_feedback_file(upload_file)
        
        assert len(comments_data) == 3
        assert all("comment" in comment for comment in comments_data)
        
        # Check data integrity
        first_comment = comments_data[0]
        assert "chips" in first_comment["comment"].lower()

    async def test_parse_invalid_file_format(self):
        """Test parsing invalid file format."""
        service = FeedbackService()
        
        upload_file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(b"invalid content")
        )
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            await service._parse_feedback_file(upload_file)

    async def test_parse_missing_required_columns(self):
        """Test parsing file with missing required columns."""
        service = FeedbackService()
        
        # CSV without required 'comment' column
        invalid_csv = b"username,sku\nuser1,PROD1\nuser2,PROD2"
        upload_file = UploadFile(
            filename="invalid.csv",
            file=io.BytesIO(invalid_csv)
        )
        
        with pytest.raises(ValueError, match="Missing required columns"):
            await service._parse_feedback_file(upload_file)

    async def test_column_name_variations(self):
        """Test handling of column name variations."""
        service = FeedbackService()
        
        # CSV with Spanish column names
        spanish_csv = b"comentario,usuario,producto\n\"Muy bueno\",user1,PROD1\n\"Regular\",user2,PROD2"
        upload_file = UploadFile(
            filename="spanish.csv",
            file=io.BytesIO(spanish_csv)
        )
        
        comments_data = await service._parse_feedback_file(upload_file)
        
        assert len(comments_data) == 2
        assert "Muy bueno" in comments_data[0]["comment"]
        assert comments_data[0]["username"] == "user1"

    @patch.object(FeedbackChain, 'analyze_batch')
    @patch.object(FeedbackChain, 'aggregate_results')
    async def test_analyze_file_complete_flow(self, mock_aggregate, mock_analyze_batch, sample_csv_content, mock_comment_analysis):
        """Test complete file analysis flow."""
        service = FeedbackService()
        
        # Mock chain responses
        mock_analyze_batch.return_value = mock_comment_analysis
        mock_aggregate.return_value = FeedbackAnalyzeResponse(
            overall_sentiment=SentimentScore(label="positive", score=0.7),
            themes=[Theme(name="sabor", examples=["test"])],
            top_issues=[],
            feature_requests=[],
            highlights=[],
            by_sku={},
            by_channel={}
        )
        
        upload_file = UploadFile(
            filename="test.csv",
            file=io.BytesIO(sample_csv_content)
        )
        
        result = await service.analyze_file(upload_file)
        
        assert isinstance(result, FeedbackAnalyzeResponse)
        mock_analyze_batch.assert_called_once()
        mock_aggregate.assert_called_once()

    @patch('app.infra.storage.storage')
    async def test_save_analysis_results(self, mock_storage):
        """Test saving analysis results."""
        service = FeedbackService()
        
        mock_storage.create_job_directory.return_value = "test-job-123"
        mock_storage.save_metadata.return_value = "path/to/metadata.json"
        
        result = FeedbackAnalyzeResponse(
            overall_sentiment=SentimentScore(label="positive", score=0.8),
            themes=[],
            top_issues=[],
            feature_requests=[],
            highlights=[],
            by_sku={},
            by_channel={}
        )
        
        job_id = await service._save_analysis_results("test.csv", result, [])
        
        assert job_id == "test-job-123"
        mock_storage.create_job_directory.assert_called_once()
        assert mock_storage.save_metadata.call_count == 2  # Two saves: results + export data

    @patch('app.infra.storage.storage')
    async def test_export_results_to_excel(self, mock_storage):
        """Test Excel export functionality."""
        service = FeedbackService()
        
        # Mock export data
        export_data = {
            "comments_data": [{"comment": "test", "username": "user1"}],
            "analysis_results": {
                "overall_sentiment": {"label": "positive", "score": 0.8},
                "themes": [{"name": "sabor", "examples": ["test"]}],
                "top_issues": [{"issue": "precio", "count": 2, "priority": "alta"}],
                "feature_requests": [{"request": "sin_sal", "count": 3}],
                "highlights": [{"quote": "excelente", "sku": "TEST", "channel": "web"}],
                "by_sku": {"TEST": {"total_comments": 1, "sentiment_distribution": {"positive": 1}, "top_themes": ["sabor"], "top_issues": []}},
                "by_channel": {"web": {"total_comments": 1, "sentiment_distribution": {"positive": 1}, "top_themes": ["sabor"], "top_issues": []}}
            }
        }
        
        mock_storage.load_metadata.return_value = export_data
        mock_storage.artifacts_path = Path("/tmp/test")
        
        # Create temporary directory structure
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            job_dir = temp_path / "test-job-123"
            job_dir.mkdir()
            
            mock_storage.artifacts_path = temp_path
            
            result = await service.export_results_to_excel("test-job-123")
            
            # Should return path to Excel file
            assert result is not None
            assert "feedback_analysis.xlsx" in result

    def test_get_analysis_info(self):
        """Test getting analysis information."""
        service = FeedbackService()
        
        with patch('app.infra.storage.storage') as mock_storage:
            mock_storage.load_metadata.return_value = {
                "input_file": "test.csv",
                "total_comments": 10,
                "processing_summary": {"overall_sentiment": {"label": "positive", "score": 0.8}}
            }
            mock_storage.list_job_artifacts.return_value = ["analysis_results.json", "export_data.json"]
            
            info = service.get_analysis_info("test-job-123")
            
            assert info is not None
            assert info["job_id"] == "test-job-123"
            assert info["input_file"] == "test.csv"
            assert info["total_comments"] == 10
            assert len(info["artifacts"]) == 2


class TestFeedbackModels:
    """Test feedback response models."""

    def test_sentiment_score_model(self):
        """Test SentimentScore model."""
        sentiment = SentimentScore(label="positive", score=0.8)
        assert sentiment.label == "positive"
        assert sentiment.score == 0.8

    def test_theme_model(self):
        """Test Theme model."""
        theme = Theme(name="sabor", examples=["muy rico", "buen sabor"])
        assert theme.name == "sabor"
        assert len(theme.examples) == 2

    def test_issue_model(self):
        """Test Issue model."""
        issue = Issue(issue="empaque", count=5, priority="alta")
        assert issue.issue == "empaque"
        assert issue.count == 5
        assert issue.priority == "alta"

    def test_feature_request_model(self):
        """Test FeatureRequest model."""
        request = FeatureRequest(request="version_familiar", count=3)
        assert request.request == "version_familiar"
        assert request.count == 3

    def test_highlight_model(self):
        """Test Highlight model."""
        highlight = Highlight(quote="Excelente producto", sku="TEST-001", channel="web")
        assert highlight.quote == "Excelente producto"
        assert highlight.sku == "TEST-001"
        assert highlight.channel == "web"

    def test_feedback_analyze_response_model(self):
        """Test complete FeedbackAnalyzeResponse model."""
        response = FeedbackAnalyzeResponse(
            overall_sentiment=SentimentScore(label="positive", score=0.8),
            themes=[Theme(name="sabor", examples=["rico"])],
            top_issues=[Issue(issue="precio", count=2, priority="media")],
            feature_requests=[FeatureRequest(request="sin_sal", count=1)],
            highlights=[Highlight(quote="test", sku="TEST", channel="web")],
            by_sku={"TEST": {"total": 1}},
            by_channel={"web": {"total": 1}}
        )
        
        assert response.overall_sentiment.label == "positive"
        assert len(response.themes) == 1
        assert len(response.top_issues) == 1
        assert len(response.feature_requests) == 1
        assert len(response.highlights) == 1
        assert "TEST" in response.by_sku
        assert "web" in response.by_channel