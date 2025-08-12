# Healthy Snack IA

AI-powered snack marketing content generator using FastAPI and LangChain.

## Phase 1 - Product Descriptions Generation ✅

### Features
- LangChain-based descriptions generation with structured output
- Multi-channel content (E-commerce, MercadoLibre, Instagram)
- Content guardrails and compliance validation
- Human-readable logging with correlation IDs
- Comprehensive test coverage

## Phase 2 - Promotional Images Generation 🎨 ✅

### Features
- **OpenAI DALL-E 3 API** integration for high-quality image generation
- **Smart prompt optimization** based on brand style and aspect ratio
- **Multiple aspect ratios** support (1:1, 16:9, 9:16)
- **Artifact storage system** with metadata persistence
- **Image download and regeneration** capabilities
- **Health monitoring** for image services
- **Comprehensive test coverage** with mocks

## Phase 3 - Feedback Analysis and Insights 📊 ✅

### Features
- **LangChain-powered sentiment analysis** with GPT-4o
- **CSV/XLSX file upload** and intelligent parsing
- **Concurrent processing** with configurable semaphore limits
- **Smart theme extraction** and issue prioritization
- **Feature request detection** from user comments
- **Multi-dimensional aggregation** (by SKU, channel, sentiment)
- **Excel export** with multiple analysis sheets
- **Comprehensive insights** with actionable recommendations

## Phase 4 - Interactive Frontend with Gradio 🎨

### Features
- **3-tab interface** covering all functionality
- **Real-time API integration** with status monitoring
- **Interactive forms** with validation and guidance
- **File upload and download** capabilities
- **Visual results display** with JSON formatting
- **Responsive design** with modern UI components
- **Error handling** with user-friendly messages
- **Auto-download** of generated artifacts

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

4. Check services:
```bash
curl http://localhost:8000/health      # API health
curl http://localhost:7860            # Frontend (Gradio UI)
```

### Access the Application

- **Frontend (Gradio UI)**: http://localhost:7860
  - Tab 1: 📝 **Descripciones** - Generate product descriptions  
  - Tab 2: 🎨 **Imágenes** - Create promotional images
  - Tab 3: 📊 **Análisis** - Analyze customer feedback

- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

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

4. Run the services:
```bash
# Terminal 1: API
python -m app.main

# Terminal 2: Frontend
cd frontend && python app.py
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

#### Analyze Customer Feedback (Phase 3)

```bash
# Upload CSV/XLSX file for analysis
curl -X POST "http://localhost:8000/v1/feedback/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@feedback_comments.csv"

# Get sample file format
curl "http://localhost:8000/v1/feedback/sample"

# Export analysis to Excel
curl -X POST "http://localhost:8000/v1/feedback/export/{job_id}"

# Download Excel analysis report
curl "http://localhost:8000/v1/feedback/download/{job_id}/feedback_analysis.xlsx" -o analysis_report.xlsx
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

**Feedback Analysis:**
```bash
# Upload feedback file
http -f POST localhost:8000/v1/feedback/analyze file@feedback_comments.csv

# Get sample format
http GET localhost:8000/v1/feedback/sample

# Check health
http GET localhost:8000/v1/feedback/health
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

**Feedback Analysis (Fase 3):**

1. **Procesamiento concurrente**: ~5-15 comentarios por segundo
   - Ajustable con MAX_CONCURRENCY (default: 5)
   - Análisis por lotes para eficiencia

2. **Tamaño de archivos**:
   - Máximo 10MB por archivo
   - Soporte CSV y XLSX
   - Hasta ~1000 comentarios recomendado para mejor performance

3. **Calidad de análisis**:
   - Comentarios entre 5-1000 caracteres
   - Mejor precisión con contexto (SKU, channel)
   - Análisis multilingüe (optimizado para español)

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
| **OPENAI_IMAGE_MODEL** | dall-e-3 | OpenAI image generation model |
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
- `app/infra/image_providers/openai_dalle.py` - OpenAI DALL-E API provider
- `app/infra/storage.py` - Artifacts storage service
- `app/domain/chains/images_chain.py` - Image generation chain
- `app/domain/services/images_service.py` - Images service layer
- `app/api/routers/images.py` - Images API endpoints
- `app/tests/test_images.py` - Comprehensive images tests
- `app/domain/prompts/system_visual.md` - Visual guidelines

**Phase 3 (Feedback Analysis):**
- `app/domain/chains/feedback_chain.py` - LangChain feedback analysis
- `app/domain/services/feedback_service.py` - Feedback service with file processing
- `app/api/routers/feedback.py` - Feedback API endpoints with upload
- `app/tests/test_feedback.py` - Comprehensive feedback tests
- `app/domain/prompts/system_insights.md` - Analysis guidelines

**Phase 4 (Frontend):**
- `frontend/app.py` - Gradio interface with 3 tabs
- `docker/Dockerfile.frontend` - Frontend Docker configuration
- Updated `docker-compose.yml` - Full stack deployment

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
