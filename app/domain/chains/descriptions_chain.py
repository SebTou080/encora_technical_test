"""LangChain-based descriptions generation chain with structured output."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...core.config import settings
from ...core.logging import get_logger
from ..models.descriptions import (
    ComplianceInfo,
    DescriptionGenerateRequest,
    DescriptionGenerateResponse,
    EcommerceDescription,
    InstagramDescription,
    MercadoLibreDescription,
    SEOMetadata,
    TraceInfo,
)

logger = get_logger(__name__)


class ChannelDescriptions(BaseModel):
    """Structured output model for all channel descriptions."""
    ecommerce: EcommerceDescription = Field(..., description="E-commerce description")
    mercado_libre: MercadoLibreDescription = Field(..., description="MercadoLibre description")  
    instagram: InstagramDescription = Field(..., description="Instagram description")


class DescriptionsChain:
    """LangChain-based chain for generating product descriptions."""

    def __init__(self) -> None:
        """Initialize the descriptions chain."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            timeout=settings.request_timeout_s,
            max_retries=1,  # Reduce retries for faster response
            request_timeout=30,  # 30s timeout per request
        )
        self.parser = PydanticOutputParser(pydantic_object=ChannelDescriptions)
        self.prompt = self._create_prompt()
        self.chain = self.prompt | self.llm | self.parser
        
        # Load brand guidelines and guardrails
        self.brand_guidelines = self._load_brand_guidelines()
        self.guardrails = self._load_guardrails()

    def _create_prompt(self) -> PromptTemplate:
        """Create the prompt template for descriptions generation."""
        template = """
Eres un copywriter experto especializado en productos de snacks saludables.

INFORMACIÓN DEL PRODUCTO:
- Nombre: {product_name}
- SKU: {sku}
- Marca: {brand}
- Categoría: {category}
- Características: {features}
- Ingredientes: {ingredients}
- Información nutricional: {nutrition_facts}
- Público objetivo: {target_audience}
- Tono deseado: {tone}
- Idioma: {language}

CANALES REQUERIDOS: {channels}

DIRECTRICES DE MARCA:
{brand_guidelines}

POLÍTICAS Y RESTRICCIONES:
{guardrails}

Genera descripciones optimizadas para cada canal solicitado siguiendo estas especificaciones:

ECOMMERCE:
- Título: máximo 80 caracteres, beneficio principal
- Descripción corta: 150-200 caracteres, hook emocional
- Descripción larga: 300-500 palabras, storytelling + especificaciones
- Bullets: 3-5 puntos de beneficios concretos
- SEO: keywords relevantes, meta title (60 chars), meta description (150-160 chars)

MERCADOLIBRE:  
- Título: máximo 60 caracteres, keywords de búsqueda
- Bullets: 5-7 puntos concisos de características y beneficios

INSTAGRAM:
- Caption: 100-150 palabras conversacionales
- Hashtags: 8-12 hashtags relevantes (mix popular/nicho)

IMPORTANTE:
- Adapta el tono al público objetivo
- Menciona beneficios antes que características  
- Usa datos específicos cuando sea posible
- Evita claims médicos no respaldados
- Mantén el tono {tone}

{format_instructions}
"""
        return PromptTemplate(
            template=template,
            input_variables=[
                "product_name", "sku", "brand", "category", "features",
                "ingredients", "nutrition_facts", "target_audience", "tone",
                "language", "channels", "brand_guidelines", "guardrails"
            ],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

    def _load_brand_guidelines(self) -> str:
        """Load brand guidelines from markdown file."""
        try:
            guidelines_path = Path(__file__).parent.parent / "prompts" / "system_copywriter.md"
            return guidelines_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to load brand guidelines: {e}")
            return "Usar tono cálido y experto, enfocarse en beneficios del producto."

    def _load_guardrails(self) -> str:
        """Load content guardrails from markdown file."""
        try:
            guardrails_path = Path(__file__).parent.parent / "prompts" / "policy_guardrails.md"
            return guardrails_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to load guardrails: {e}")
            return "Evitar claims médicos no respaldados. Mantener tono inclusivo."

    def _validate_content(self, descriptions: ChannelDescriptions) -> ComplianceInfo:
        """Validate content against guardrails."""
        prohibited_words = [
            "cura", "trata", "previene enfermedades", "milagroso", "mágico",
            "elimina toxinas", "100% efectivo", "garantizado"
        ]
        
        health_claims = []
        all_text = ""
        
        # Collect all text for analysis
        if hasattr(descriptions, 'ecommerce'):
            all_text += f" {descriptions.ecommerce.title} {descriptions.ecommerce.short_description} {descriptions.ecommerce.long_description}"
        
        # Check for prohibited words
        text_lower = all_text.lower()
        for word in prohibited_words:
            if word in text_lower:
                health_claims.append(f"Prohibited word found: {word}")
        
        # Simple readability check (average sentence length)
        sentences = all_text.split('.')
        avg_words_per_sentence = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        reading_level = "B1" if avg_words_per_sentence < 20 else "B2"
        
        return ComplianceInfo(
            health_claims=health_claims,
            reading_level=reading_level
        )

    async def generate(self, request: DescriptionGenerateRequest) -> DescriptionGenerateResponse:
        """Generate product descriptions for specified channels."""
        try:
            # Prepare input data
            input_data = {
                "product_name": request.product_name,
                "sku": request.sku,
                "brand": request.brand,
                "category": request.category,
                "features": ", ".join(request.features),
                "ingredients": ", ".join(request.ingredients),
                "nutrition_facts": request.nutrition_facts.model_dump() if request.nutrition_facts else "No disponible",
                "target_audience": request.target_audience or "Consumidores conscientes de su salud",
                "tone": request.tone,
                "language": request.language,
                "channels": ", ".join(request.channels),
                "brand_guidelines": self.brand_guidelines,
                "guardrails": self.guardrails,
            }

            # Generate descriptions
            logger.info(f"🤖 Calling LLM for {request.sku}...")
            result = await self.chain.ainvoke(input_data)
            logger.info(f"✨ LLM response received for {request.sku}")
            
            # Validate content
            logger.info(f"🛡️ Validating content compliance for {request.sku}...")
            compliance = self._validate_content(result)
            if compliance.health_claims:
                logger.warning(f"⚠️ Found {len(compliance.health_claims)} compliance issues for {request.sku}")
            else:
                logger.info(f"✅ Content compliance passed for {request.sku}")
            
            # Build response based on requested channels
            by_channel = {}
            
            if "ecommerce" in request.channels:
                by_channel["ecommerce"] = result.ecommerce.model_dump()
            
            if "mercado_libre" in request.channels:
                by_channel["mercado_libre"] = result.mercado_libre.model_dump()
                
            if "instagram" in request.channels:
                by_channel["instagram"] = result.instagram.model_dump()

            # Create trace info
            trace = TraceInfo(
                model=settings.openai_model,
                input_tokens=0,  # Would need to implement token counting
                output_tokens=0
            )

            return DescriptionGenerateResponse(
                sku=request.sku,
                language=request.language,
                by_channel=by_channel,
                compliance=compliance,
                trace=trace
            )

        except Exception as e:
            logger.error(f"💥 LLM call failed for {request.sku}: {e}")
            raise