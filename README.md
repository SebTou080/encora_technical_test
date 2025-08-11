# Healthy Snack IA

AI-powered snack marketing content generator using FastAPI and LangChain.

## Phase 1 - Product Descriptions Generation ✅

### Features
- LangChain-based descriptions generation with structured output
- Multi-channel content (E-commerce, MercadoLibre, Instagram)
- Content guardrails and compliance validation
- Human-readable logging with correlation IDs
- Comprehensive test coverage

## Phase 2 - Promotional Images Generation 🎨

### Features
- **Hugging Face Inference API** integration (FLUX.1-schnell model)
- **Smart prompt optimization** based on brand style and aspect ratio
- **Multiple aspect ratios** support (1:1, 16:9, 9:16, 4:3, 3:4)
- **Artifact storage system** with metadata persistence
- **Image download and regeneration** capabilities
- **Health monitoring** for image services
- **Comprehensive test coverage** with mocks

### Quick Start

#### With Docker Compose (Recommended)

1. Copy environment configuration:
```bash
cp configs/.env.example configs/.env
```

2. Edit `configs/.env` and add your OpenAI API key:
```bash
OPENAI_API_KEY=your-openai-api-key-here
```

3. Start the services:
```bash
docker-compose up -d
```

4. Check health:
```bash
curl http://localhost:8000/health
```

#### Local Development

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Set up pre-commit hooks:
```bash
pre-commit install
```

3. Copy and configure environment:
```bash
cp configs/.env.example configs/.env
# Edit configs/.env with your API keys
```

4. Run the API:
```bash
python -m app.main
```

### API Usage

#### Generate Product Descriptions

```bash
curl -X POST "http://localhost:8000/v1/descriptions/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Chips de Kale al Horno",
    "sku": "KALE-90G",
    "brand": "GreenBite",
    "language": "es",
    "channels": ["ecommerce", "mercado_libre", "instagram"],
    "target_audience": "adultos conscientes de su salud",
    "category": "snacks_saludables",
    "features": ["horneado", "sin fritura", "vegano", "sin gluten"],
    "ingredients": ["kale", "aceite de oliva", "sal marina"],
    "nutrition_facts": {
      "calories": 90,
      "protein_g": 3,
      "fat_g": 4,
      "carbs_g": 10
    },
    "tone": "cálido y experto",
    "variants": 1
  }'
```

#### Generate Promotional Images (Phase 2)

```bash
curl -X POST "http://localhost:8000/v1/images/generate" \
  -H "Content-Type: multipart/form-data" \
  -F "prompt_brief=Chips de Kale crujientes sobre superficie de madera clara con ingredientes frescos" \
  -F "brand_style={\"colors\": [\"verde natural\", \"blanco\"], \"style\": \"organic premium\"}" \
  -F "aspect_ratio=1:1" \
  -F "seed=12345"
```

#### Download Generated Images

```bash
# Get artifact info
curl "http://localhost:8000/v1/images/artifacts/{job_id}"

# Download image
curl "http://localhost:8000/v1/images/artifacts/{job_id}/download/image.png" -o generated_image.png

# Download metadata
curl "http://localhost:8000/v1/images/artifacts/{job_id}/download/metadata.json" -o metadata.json
```

#### Using HTTPie (Alternative)

**Descriptions:**
```bash
http POST localhost:8000/v1/descriptions/generate \
  product_name="Chips de Kale al Horno" \
  sku="KALE-90G" \
  brand="GreenBite" \
  language="es" \
  channels:='["ecommerce", "mercado_libre", "instagram"]' \
  target_audience="adultos conscientes de su salud" \
  category="snacks_saludables" \
  features:='["horneado", "sin fritura", "vegano", "sin gluten"]' \
  ingredients:='["kale", "aceite de oliva", "sal marina"]' \
  nutrition_facts:='{"calories": 90, "protein_g": 3, "fat_g": 4, "carbs_g": 10}' \
  tone="cálido y experto" \
  variants:=1
```

**Images:**
```bash
http -f POST localhost:8000/v1/images/generate \
  prompt_brief="Chips de Kale crujientes, fotografía profesional de producto" \
  brand_style="estilo orgánico premium con colores naturales" \
  aspect_ratio="1:1" \
  seed:=12345
```

### Rendimiento y Optimización

**Descripciones (Fase 1):**

1. **Variantes**: Para mayor velocidad, usa `variants: 1` (predeterminado)
   - 1 variante: ~15-30 segundos
   - 3 variantes: ~45-90 segundos (procesamiento concurrente) 

2. **Modelo OpenAI**: 
   - `gpt-4o`: Más lento pero mejor calidad
   - `gpt-3.5-turbo`: Más rápido para pruebas

3. **Canales**: Solicita solo los canales necesarios para reducir tiempo de procesamiento

**Imágenes (Fase 2):**

1. **Tiempo de generación**: ~20-60 segundos dependiendo del modelo HF
   - Primera llamada puede tardar más (carga del modelo)
   - Llamadas subsequentes más rápidas

2. **Aspect ratios optimizados**:
   - `1:1`: Redes sociales (Instagram, Facebook)
   - `16:9`: Banners, headers web
   - `9:16`: Stories, móvil vertical

3. **Prompts efectivos**:
   - Ser específico pero conciso
   - Incluir estilo fotográfico deseado
   - Usar brand_style para consistencia

### Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

Run linting and formatting:
```bash
ruff check app/
black app/
mypy app/
```

### Project Structure

```
app/
├── api/                    # FastAPI routes and middleware
│   ├── routers/
│   │   └── descriptions.py # Descriptions endpoint
│   ├── deps.py            # Dependency injection
│   ├── errors.py          # Error handling
│   └── middleware.py      # Correlation ID middleware
├── core/                  # Core configuration
│   ├── config.py         # Settings management
│   └── logging.py        # JSON logging setup
├── domain/               # Business logic
│   ├── models/           # Pydantic models
│   ├── chains/           # LangChain chains
│   ├── services/         # Service layer
│   └── prompts/          # Prompt templates
├── tests/                # Test suite
└── main.py              # FastAPI app entry point

configs/
├── .env.example          # Environment variables template
├── brand_guidelines.json # Brand voice and guidelines
└── channel_presets.json  # Channel-specific requirements

docker/
└── Dockerfile.api        # API service Dockerfile
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OPENAI_API_KEY | changeme | OpenAI API key |
| OPENAI_MODEL | gpt-4o | OpenAI model name |
| **HF_MODEL_URL** | FLUX.1-schnell | Hugging Face model URL |
| **HF_TOKEN** | - | Hugging Face API token |
| LOG_LEVEL | INFO | Logging level |
| API_HOST | 0.0.0.0 | API host |
| API_PORT | 8000 | API port |
| REQUEST_TIMEOUT_S | 60 | Request timeout in seconds |
| **MAX_CONCURRENCY** | 5 | Maximum concurrent requests |

### Files Created

**Phase 1 (Descriptions):**
- `app/domain/chains/descriptions_chain.py` - LangChain descriptions generation
- `app/domain/services/descriptions_service.py` - Descriptions service layer
- `app/api/routers/descriptions.py` - Descriptions API endpoints
- `app/tests/test_descriptions.py` - Comprehensive descriptions tests

**Phase 2 (Images):**
- `app/infra/image_providers/hf_inference.py` - Hugging Face API provider
- `app/infra/storage.py` - Artifacts storage service
- `app/domain/chains/images_chain.py` - Image generation chain
- `app/domain/services/images_service.py` - Images service layer
- `app/api/routers/images.py` - Images API endpoints
- `app/tests/test_images.py` - Comprehensive images tests
- `app/domain/prompts/system_visual.md` - Visual guidelines

**Core Infrastructure:**
- `pyproject.toml` - Python project configuration
- `docker-compose.yml` - Docker services configuration
- `app/main.py` - FastAPI application entry point
- `app/core/` - Configuration and human-readable logging
- `app/api/middleware.py` - Correlation-id middleware
- `configs/` - Brand guidelines and environment configuration
- `docker/` - Docker configuration files

## License

MIT License# encora_technical_test
