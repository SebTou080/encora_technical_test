"""Tests for images functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import httpx

from ..domain.models.images import ImageGenerateRequest, ImageGenerateResponse
from ..domain.services.images_service import ImagesService
from ..domain.chains.images_chain import ImagesChain
from ..infra.image_providers.openai_dalle import OpenAIImageProvider, OpenAIImageResponse
from ..infra.storage import StorageService


@pytest.fixture
def sample_image_request():
    """Sample image generation request."""
    return ImageGenerateRequest(
        prompt_brief="Chips de Quinoa Crujiente sobre superficie de madera clara",
        aspect_ratio="1:1",
        seed=12345
    )


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI image response."""
    return OpenAIImageResponse(
        image_bytes=b"fake_png_data_here_12345",
        content_type="image/png",
        model="dall-e-3",
        prompt="Professional product photography of Chips de Quinoa...",
        revised_prompt="Professional product photography of Chips de Quinoa Crujiente...",
        meta={
            "job_id": "test-job-123",
            "size": "1024x1024",
            "quality": "hd",
            "style": "natural",
            "response_size_bytes": 25
        }
    )


@pytest.fixture
def mock_storage_service():
    """Mock storage service."""
    mock_storage = MagicMock(spec=StorageService)
    mock_storage.create_job_directory.return_value = "test-job-123"
    mock_storage.save_image.return_value = "./data/artifacts/test-job-123/image.png"
    mock_storage.save_metadata.return_value = "./data/artifacts/test-job-123/metadata.json"
    mock_storage.load_metadata.return_value = {"test": "metadata"}
    mock_storage.list_job_artifacts.return_value = ["image.png", "metadata.json"]
    mock_storage.get_artifact_path.return_value = "/app/data/artifacts/test-job-123/image.png"
    return mock_storage


class TestOpenAIImageProvider:
    """Test OpenAI DALL-E API provider."""

    @patch('httpx.AsyncClient.post')
    @patch('httpx.AsyncClient.get')
    async def test_generate_image_success(self, mock_get, mock_post, sample_image_request):
        """Test successful image generation via OpenAI API."""
        # Mock API response
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {
            "data": [{
                "url": "https://example.com/generated-image.png",
                "revised_prompt": "Revised prompt here"
            }]
        }
        mock_post.return_value = mock_api_response
        
        # Mock image download response
        mock_image_response = MagicMock()
        mock_image_response.status_code = 200
        mock_image_response.content = b"fake_png_data"
        mock_image_response.headers = {"content-type": "image/png"}
        mock_get.return_value = mock_image_response
        
        provider = OpenAIImageProvider()
        result = await provider.generate_image(
            prompt=sample_image_request.prompt_brief,
            size="1024x1024"
        )
        
        assert isinstance(result, OpenAIImageResponse)
        assert result.image_bytes == b"fake_png_data"
        assert result.content_type == "image/png"
        assert result.model == "dall-e-3"
        mock_post.assert_called_once()
        mock_get.assert_called_once()

    @patch('httpx.AsyncClient.post')
    async def test_generate_image_api_error(self, mock_post):
        """Test OpenAI API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        provider = OpenAIImageProvider()
        
        with pytest.raises(Exception) as exc_info:
            await provider.generate_image(prompt="test prompt")
        
        assert "OpenAI API error: 400" in str(exc_info.value)

    @patch('httpx.AsyncClient.get')
    async def test_health_check_success(self, mock_get):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        provider = OpenAIImageProvider()
        result = await provider.health_check()
        
        assert result is True

    @patch('httpx.AsyncClient.get')
    async def test_health_check_failure(self, mock_get):
        """Test health check failure."""
        mock_get.side_effect = httpx.RequestError("Connection failed")
        
        provider = OpenAIImageProvider()
        result = await provider.health_check()
        
        assert result is False


class TestStorageService:
    """Test storage service functionality."""

    def test_create_job_directory(self, tmp_path, monkeypatch):
        """Test job directory creation."""
        monkeypatch.chdir(tmp_path)
        
        storage = StorageService(base_path=str(tmp_path / "test_storage"))
        job_id = storage.create_job_directory("test-job-123")
        
        assert job_id == "test-job-123"
        assert (tmp_path / "test_storage" / "artifacts" / "test-job-123").exists()

    def test_save_and_load_image(self, tmp_path, monkeypatch):
        """Test image saving and loading."""
        monkeypatch.chdir(tmp_path)
        
        storage = StorageService(base_path=str(tmp_path / "test_storage"))
        job_id = storage.create_job_directory("test-job-123")
        
        image_data = b"fake_image_data"
        path = storage.save_image(job_id, image_data, "test.png")
        
        # Verify file exists and content is correct
        full_path = tmp_path / "test_storage" / "artifacts" / "test-job-123" / "test.png"
        assert full_path.exists()
        assert full_path.read_bytes() == image_data

    def test_save_and_load_metadata(self, tmp_path, monkeypatch):
        """Test metadata saving and loading."""
        monkeypatch.chdir(tmp_path)
        
        storage = StorageService(base_path=str(tmp_path / "test_storage"))
        job_id = storage.create_job_directory("test-job-123")
        
        metadata = {"prompt": "test", "seed": 123}
        storage.save_metadata(job_id, metadata)
        
        loaded_metadata = storage.load_metadata(job_id)
        assert loaded_metadata == metadata


class TestImagesChain:
    """Test images chain functionality."""

    @patch('app.infra.storage.storage')
    @patch.object(OpenAIImageProvider, 'generate_image')
    async def test_generate_image(self, mock_openai_generate, mock_storage, sample_image_request, mock_openai_response):
        """Test image generation through chain."""
        # Mock storage
        mock_storage.create_job_directory.return_value = "test-job-123"
        mock_storage.save_image.return_value = "./data/artifacts/test-job-123/image.png"
        mock_storage.save_metadata.return_value = "./data/artifacts/test-job-123/metadata.json"
        
        # Mock OpenAI provider
        mock_openai_generate.return_value = mock_openai_response
        
        chain = ImagesChain()
        result = await chain.generate(sample_image_request)
        
        assert isinstance(result, ImageGenerateResponse)
        assert result.job_id == "test-job-123"
        assert result.width == 1024
        assert result.height == 1024
        
        # Verify storage calls
        mock_storage.create_job_directory.assert_called_once()
        mock_storage.save_image.assert_called_once()
        mock_storage.save_metadata.assert_called_once()

    def test_optimize_prompt_with_brand_style(self, sample_image_request):
        """Test prompt optimization with brand style."""
        chain = ImagesChain()
        optimized = chain._optimize_prompt(sample_image_request)
        
        assert "Professional product photography" in optimized
        assert "photorealistic" in optimized
        assert "studio quality" in optimized

    def test_calculate_dimensions_various_ratios(self):
        """Test dimension calculations for different aspect ratios."""
        chain = ImagesChain()
        
        # Test various aspect ratios
        assert chain._calculate_dimensions("1:1") == (1024, 1024)
        assert chain._calculate_dimensions("16:9") == (1792, 1024)
        assert chain._calculate_dimensions("9:16") == (1024, 1792)
        assert chain._calculate_dimensions("4:3") == (1024, 1024)
        assert chain._calculate_dimensions("3:4") == (1024, 1024)


class TestImagesService:
    """Test images service functionality."""

    @patch.object(ImagesChain, 'generate')
    async def test_generate_image_success(self, mock_chain_generate, sample_image_request):
        """Test successful image generation through service."""
        mock_response = ImageGenerateResponse(
            job_id="test-job-123",
            artifact_path="./data/artifacts/test-job-123/image.png",
            width=1024,
            height=1024,
            provider="hf",
            model_url="https://test-model.com",
            meta={"test": "meta"}
        )
        mock_chain_generate.return_value = mock_response
        
        service = ImagesService()
        result = await service.generate_image(sample_image_request)
        
        assert result.job_id == "test-job-123"
        mock_chain_generate.assert_called_once_with(sample_image_request)

    async def test_generate_image_invalid_aspect_ratio(self, sample_image_request):
        """Test validation of invalid aspect ratio."""
        sample_image_request.aspect_ratio = "invalid:ratio"
        
        service = ImagesService()
        
        with pytest.raises(ValueError, match="Unsupported aspect ratio"):
            await service.generate_image(sample_image_request)

    async def test_generate_image_invalid_seed(self, sample_image_request):
        """Test validation of invalid seed."""
        sample_image_request.seed = -1
        
        service = ImagesService()
        
        with pytest.raises(ValueError, match="Seed must be between"):
            await service.generate_image(sample_image_request)

    @patch.object(OpenAIImageProvider, 'health_check')
    @patch('app.infra.storage.storage.get_storage_stats')
    async def test_health_check_all_healthy(self, mock_storage_stats, mock_openai_health):
        """Test health check when all services are healthy."""
        mock_openai_health.return_value = True
        mock_storage_stats.return_value = {"total_jobs": 5, "total_files": 10}
        
        service = ImagesService()
        result = await service.health_check()
        
        assert result["status"] == "healthy"
        assert result["services"]["openai_dalle"]["status"] == "healthy"
        assert result["services"]["storage"]["status"] == "healthy"

    @patch.object(ImagesService, 'get_artifact_info')
    async def test_regenerate_image(self, mock_get_artifact, sample_image_request):
        """Test image regeneration."""
        # Mock existing job metadata
        mock_get_artifact.return_value = {
            "metadata": {"request": sample_image_request.model_dump()}
        }
        
        service = ImagesService()
        
        # Mock the generate_image method to avoid actual generation
        with patch.object(service, 'generate_image') as mock_generate:
            mock_response = ImageGenerateResponse(
                job_id="new-job-456",
                artifact_path="./data/artifacts/new-job-456/image.png",
                width=1024,
                height=1024
            )
            mock_generate.return_value = mock_response
            
            # Mock load_metadata to return the original request
            with patch('app.infra.storage.storage.load_metadata') as mock_load_meta:
                mock_load_meta.return_value = {"request": sample_image_request.model_dump()}
                
                result = await service.regenerate_image(
                    "old-job-123", 
                    {"prompt_brief": "new improved prompt"}
                )
                
                assert result.job_id == "new-job-456"
                mock_generate.assert_called_once()


class TestImagesAPI:
    """Test images API endpoints."""

    def test_generate_image_endpoint(self, client):
        """Test image generation endpoint."""
        # This would require more complex mocking of the entire chain
        # For now, we'll test the basic structure
        pass

    def test_health_endpoint(self, client):
        """Test images health endpoint."""
        # This would require mocking the service health check
        pass


# Additional fixtures for integration tests
@pytest.fixture
def client():
    """Test client for API endpoints."""
    from ..main import app
    return TestClient(app)