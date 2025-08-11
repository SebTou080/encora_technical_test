"""Tests for images functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import httpx

from ..domain.models.images import ImageGenerateRequest, ImageGenerateResponse
from ..domain.services.images_service import ImagesService
from ..domain.chains.images_chain import ImagesChain
from ..infra.image_providers.hf_inference import HuggingFaceInferenceProvider, HFImageResponse
from ..infra.storage import StorageService


@pytest.fixture
def sample_image_request():
    """Sample image generation request."""
    return ImageGenerateRequest(
        prompt_brief="Chips de Quinoa Crujiente sobre superficie de madera clara",
        brand_style='{"colors": ["verde natural", "blanco"], "style": "organic premium"}',
        aspect_ratio="1:1",
        seed=12345
    )


@pytest.fixture
def mock_hf_response():
    """Mock HF image response."""
    return HFImageResponse(
        image_bytes=b"fake_png_data_here_12345",
        content_type="image/png",
        model_url="https://api-inference.huggingface.co/models/test-model",
        prompt="Professional product photography of Chips de Quinoa...",
        seed=12345,
        meta={
            "job_id": "test-job-123",
            "width": 1024,
            "height": 1024,
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


class TestHuggingFaceInferenceProvider:
    """Test HF Inference API provider."""

    @patch('httpx.AsyncClient.post')
    async def test_generate_image_success(self, mock_post, sample_image_request):
        """Test successful image generation via HF API."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_png_data"
        mock_response.headers = {"content-type": "image/png"}
        mock_post.return_value = mock_response
        
        provider = HuggingFaceInferenceProvider()
        result = await provider.generate_image(
            prompt=sample_image_request.prompt_brief,
            seed=sample_image_request.seed
        )
        
        assert isinstance(result, HFImageResponse)
        assert result.image_bytes == b"fake_png_data"
        assert result.content_type == "image/png"
        assert result.seed == sample_image_request.seed
        mock_post.assert_called_once()

    @patch('httpx.AsyncClient.post')
    async def test_generate_image_model_loading_retry(self, mock_post):
        """Test HF API model loading scenario with retry."""
        # First response: 503 (model loading)
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.text = "Model is loading"
        
        # Second response: 200 (success)
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.content = b"success_image_data"
        mock_response_200.headers = {"content-type": "image/png"}
        
        mock_post.side_effect = [mock_response_503, mock_response_200]
        
        provider = HuggingFaceInferenceProvider()
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await provider.generate_image(prompt="test prompt")
            
            assert result.image_bytes == b"success_image_data"
            mock_sleep.assert_called_once_with(20)
            assert mock_post.call_count == 2

    @patch('httpx.AsyncClient.post')
    async def test_generate_image_api_error(self, mock_post):
        """Test HF API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        provider = HuggingFaceInferenceProvider()
        
        with pytest.raises(Exception) as exc_info:
            await provider.generate_image(prompt="test prompt")
        
        assert "HF API error: 400" in str(exc_info.value)

    @patch('httpx.AsyncClient.post')
    async def test_health_check_success(self, mock_post):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        provider = HuggingFaceInferenceProvider()
        result = await provider.health_check()
        
        assert result is True

    @patch('httpx.AsyncClient.post')
    async def test_health_check_failure(self, mock_post):
        """Test health check failure."""
        mock_post.side_effect = httpx.RequestError("Connection failed")
        
        provider = HuggingFaceInferenceProvider()
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
    @patch.object(HuggingFaceInferenceProvider, 'generate_image')
    async def test_generate_image(self, mock_hf_generate, mock_storage, sample_image_request, mock_hf_response):
        """Test image generation through chain."""
        # Mock storage
        mock_storage.create_job_directory.return_value = "test-job-123"
        mock_storage.save_image.return_value = "./data/artifacts/test-job-123/image.png"
        mock_storage.save_metadata.return_value = "./data/artifacts/test-job-123/metadata.json"
        
        # Mock HF provider
        mock_hf_generate.return_value = mock_hf_response
        
        chain = ImagesChain()
        result = await chain.generate(sample_image_request)
        
        assert isinstance(result, ImageGenerateResponse)
        assert result.job_id == "test-job-123"
        assert result.width == 1024
        assert result.height == 1024
        assert result.provider == "hf"
        
        # Verify storage calls
        mock_storage.create_job_directory.assert_called_once()
        mock_storage.save_image.assert_called_once()
        mock_storage.save_metadata.assert_called_once()

    def test_optimize_prompt_with_brand_style(self, sample_image_request):
        """Test prompt optimization with brand style."""
        chain = ImagesChain()
        optimized = chain._optimize_prompt(sample_image_request)
        
        assert "Professional product photography" in optimized
        assert "verde natural" in optimized
        assert "photorealistic" in optimized
        assert "studio quality" in optimized

    def test_calculate_dimensions_various_ratios(self):
        """Test dimension calculations for different aspect ratios."""
        chain = ImagesChain()
        
        # Test various aspect ratios
        assert chain._calculate_dimensions("1:1") == (1024, 1024)
        assert chain._calculate_dimensions("16:9") == (1024, 576)
        assert chain._calculate_dimensions("9:16") == (576, 1024)
        assert chain._calculate_dimensions("4:3") == (1024, 768)


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

    @patch.object(HuggingFaceInferenceProvider, 'health_check')
    @patch('app.infra.storage.storage.get_storage_stats')
    async def test_health_check_all_healthy(self, mock_storage_stats, mock_hf_health):
        """Test health check when all services are healthy."""
        mock_hf_health.return_value = True
        mock_storage_stats.return_value = {"total_jobs": 5, "total_files": 10}
        
        service = ImagesService()
        result = await service.health_check()
        
        assert result["status"] == "healthy"
        assert result["services"]["huggingface_inference"]["status"] == "healthy"
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
                height=1024,
                provider="hf",
                model_url="https://test-model.com",
                meta={"regenerated": True}
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