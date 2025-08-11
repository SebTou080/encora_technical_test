# Healthy Snack IA

AI-powered snack marketing content generator using FastAPI and LangChain.

## Phase 1 - Product Descriptions Generation

### Features
- LangChain-based descriptions generation with structured output
- Multi-channel content (E-commerce, MercadoLibre, Instagram)
- Content guardrails and compliance validation
- JSON structured logging with correlation IDs
- Comprehensive test coverage

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

#### Using HTTPie (Alternative)

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

### Rendimiento y Optimización

**Recomendaciones importantes:**

1. **Variantes**: Para mayor velocidad, usa `variants: 1` (predeterminado)
   - 1 variante: ~15-30 segundos
   - 3 variantes: ~45-90 segundos (procesamiento concurrente) 

2. **Modelo OpenAI**: 
   - `gpt-4o`: Más lento pero mejor calidad
   - `gpt-3.5-turbo`: Más rápido para pruebas

3. **Canales**: Solicita solo los canales necesarios para reducir tiempo de procesamiento

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
| LOG_LEVEL | INFO | Logging level |
| API_HOST | 0.0.0.0 | API host |
| API_PORT | 8000 | API port |
| REQUEST_TIMEOUT_S | 60 | Request timeout in seconds |

### Phase 1 Files Created

- `pyproject.toml` - Python project configuration
- `docker-compose.yml` - Docker services configuration
- `app/main.py` - FastAPI application entry point
- `app/core/` - Configuration and logging modules
- `app/domain/` - Business logic and LangChain integration
- `app/api/` - FastAPI routes and middleware
- `app/tests/` - Comprehensive test suite
- `configs/` - Brand guidelines and environment configuration
- `docker/` - Docker configuration files

## License

MIT License# encora_technical_test
