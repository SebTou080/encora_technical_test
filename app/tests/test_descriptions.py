"""Tests for descriptions functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ..domain.models.descriptions import (
    DescriptionGenerateRequest,
    DescriptionGenerateResponse,
    NutritionFacts,
)
from ..domain.services.descriptions_service import DescriptionsService
from ..domain.chains.descriptions_chain import DescriptionsChain, ChannelDescriptions
from ..domain.models.descriptions import EcommerceDescription, MercadoLibreDescription, InstagramDescription, SEOMetadata


@pytest.fixture
def sample_request():
    """Sample description generation request."""
    return DescriptionGenerateRequest(
        product_name="Chips de Kale al Horno",
        brand="GreenBite",
        channels=["ecommerce", "mercado_libre", "instagram"],
        target_audience="adultos conscientes de su salud",
        category="snacks_saludables",
        features=["horneado", "sin fritura", "vegano", "sin gluten"],
        ingredients=["kale", "aceite de oliva", "sal marina"],
        nutrition_facts=NutritionFacts(
            calories=90,
            protein_g=3.0,
            fat_g=4.0,
            carbs_g=10.0
        ),
        tone="cálido y experto"
    )


@pytest.fixture
def mock_channel_descriptions():
    """Mock channel descriptions response."""
    return ChannelDescriptions(
        ecommerce=EcommerceDescription(
            title="Chips de Kale Horneados GreenBite - Snack Vegano Sin Gluten 90g",
            short_description="Descubre el sabor crujiente y saludable del kale horneado. Perfecto para tu bienestar diario.",
            long_description="Nuestros Chips de Kale al Horno son la perfecta combinación de sabor y nutrición. Elaborados con kale fresco y horneados cuidadosamente con aceite de oliva y sal marina, ofrecen una textura crujiente irresistible. Con 90 calorías por porción y 3g de proteína, son el snack ideal para quienes buscan cuidar su salud sin sacrificar el placer. Sin fritura, veganos y libres de gluten, perfectos para toda la familia.",
            bullets=[
                "Horneado, no frito - más saludable y crujiente",
                "Rico en nutrientes con solo 90 calorías por porción",
                "Vegano y sin gluten - apto para toda la familia",
                "Ingredientes premium: kale, aceite de oliva, sal marina"
            ],
            seo=SEOMetadata(
                keywords=["chips kale", "snack saludable", "vegano", "sin gluten"],
                meta_title="Chips de Kale Horneados - Snack Saludable Vegano | GreenBite",
                meta_description="Chips de kale horneados con aceite de oliva. Vegano, sin gluten, 90 calorías. El snack saludable perfecto para tu bienestar."
            )
        ),
        mercado_libre=MercadoLibreDescription(
            title="Chips Kale Horneados Veganos Sin Gluten GreenBite 90g",
            bullets=[
                "Snack saludable horneado, no frito",
                "Vegano y libre de gluten",
                "Solo 90 calorías por porción",
                "Con aceite de oliva premium",
                "Ideal para dietas saludables"
            ]
        ),
        instagram=InstagramDescription(
            caption="¿Antojo de algo crujiente pero saludable? 🥬✨ Nuestros Chips de Kale horneados son la respuesta perfecta. Con ingredientes simples pero poderosos: kale fresco, aceite de oliva y sal marina. Solo 90 calorías de pura satisfacción vegana. #SnackSaludable #VivaVerde",
            hashtags=["#chipsdekale", "#snacksaludable", "#vegano", "#singluten", "#greenbite", "#vivasaludable", "#crujiente", "#bienestar"]
        )
    )


class TestDescriptionsChain:
    """Test descriptions chain functionality."""

    @patch('langchain_openai.ChatOpenAI')
    async def test_generate_descriptions(self, mock_llm_class, sample_request, mock_channel_descriptions):
        """Test descriptions generation with mocked LLM."""
        # Mock LLM response
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_channel_descriptions
        mock_llm_class.return_value = mock_llm
        
        # Mock the chain
        chain = DescriptionsChain()
        chain.chain = AsyncMock(return_value=mock_channel_descriptions)
        
        # Test generation
        result = await chain.generate(sample_request)
        
        # Assertions
        assert isinstance(result, DescriptionGenerateResponse)
        assert result.product_name == sample_request.product_name
        assert result.brand == sample_request.brand
        assert "ecommerce" in result.by_channel
        assert "mercado_libre" in result.by_channel
        assert "instagram" in result.by_channel
        
        # Validate ecommerce structure
        ecommerce = result.by_channel["ecommerce"]
        assert "title" in ecommerce
        assert "short_description" in ecommerce
        assert "long_description" in ecommerce
        assert "bullets" in ecommerce
        assert "seo" in ecommerce

    def test_content_validation_prohibited_words(self, mock_channel_descriptions):
        """Test content validation catches prohibited words."""
        # Modify mock to include prohibited words
        mock_channel_descriptions.ecommerce.title = "Chips que curan todo"
        
        chain = DescriptionsChain()
        compliance = chain._validate_content(mock_channel_descriptions)
        
        assert len(compliance.health_claims) > 0
        assert any("cura" in claim.lower() for claim in compliance.health_claims)

    def test_reading_level_assessment(self, mock_channel_descriptions):
        """Test reading level assessment."""
        chain = DescriptionsChain()
        compliance = chain._validate_content(mock_channel_descriptions)
        
        assert compliance.reading_level in ["B1", "B2"]


class TestDescriptionsService:
    """Test descriptions service functionality."""

    @patch.object(DescriptionsChain, 'generate')
    async def test_generate_descriptions(self, mock_generate, sample_request):
        """Test service description generation."""
        # Mock chain response
        mock_response = DescriptionGenerateResponse(
            product_name=sample_request.product_name,
            brand=sample_request.brand,
            by_channel={"ecommerce": {"title": "Test"}},
            compliance={"health_claims": [], "reading_level": "B1"},
            trace={"model": "gpt-4o", "input_tokens": 100, "output_tokens": 200}
        )
        mock_generate.return_value = mock_response
        
        service = DescriptionsService()
        result = await service.generate_descriptions(sample_request)
        
        assert result.product_name == sample_request.product_name
        mock_generate.assert_called_once_with(sample_request)


    async def test_invalid_channels(self, sample_request):
        """Test validation of unsupported channels."""
        sample_request.channels = ["invalid_channel"]
        
        service = DescriptionsService()
        
        with pytest.raises(ValueError, match="Unsupported channels"):
            await service.generate_descriptions(sample_request)


class TestRequestValidation:
    """Test request validation."""

    def test_required_fields(self):
        """Test required fields validation."""
        with pytest.raises(ValueError):
            DescriptionGenerateRequest(
                product_name="",  # Empty name should fail
                brand="Test",
                channels=["ecommerce"],
                category="test"
            )

    def test_nutrition_facts_optional(self, sample_request):
        """Test nutrition facts are optional."""
        sample_request.nutrition_facts = None
        assert sample_request.nutrition_facts is None

    def test_default_values(self):
        """Test default values are set correctly."""
        request = DescriptionGenerateRequest(
            product_name="Test Product",
            sku="TEST-001",
            brand="Test Brand",
            channels=["ecommerce"],
            category="test"
        )
        
        assert request.language == "es"
        assert request.tone == "cálido y experto"
        assert request.variants == 1
        assert request.features == []
        assert request.ingredients == []