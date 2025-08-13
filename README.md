# Healthy Snack IA 🥜

Sistema de inteligencia artificial para la generación automatizada de contenido de marketing para snacks saludables. Utiliza modelos de OpenAI para crear descripciones de productos, imágenes promocionales y análisis de feedback de clientes.

## 🚀 Características Principales

### 📝 Generación de Descripciones
- **Contenido multicanal**: Genera descripciones optimizadas para diferentes canales (e-commerce, redes sociales, packaging)
- **Personalización por marca**: Sigue guidelines específicos de voz y tono de marca
- **Optimización SEO**: Incluye palabras clave relevantes y estructura optimizada
- **Múltiples variantes**: Genera diferentes versiones para A/B testing

### 🎨 Creación de Imágenes
- **Generación con DALL-E 3**: Crea imágenes promocionales de alta calidad
- **Múltiples formatos**: Soporte para diferentes aspect ratios (1:1, 16:9, 9:16, 4:3, 3:4)
- **Consistencia visual**: Mantiene coherencia con guidelines de marca
- **Descarga automática**: Almacenamiento y descarga de artefactos generados

### 📊 Análisis de Feedback
- **Procesamiento masivo**: Analiza archivos CSV/XLSX con miles de comentarios
- **Análisis de sentimiento**: Clasificación automática (positivo, neutral, negativo)
- **Extracción de insights**: Identifica temas, issues y feature requests
- **Reportes detallados**: Genera análisis agregados por SKU, canal y tiempo
- **Exportación**: Descarga resultados en formato Excel

## 🏗️ Arquitectura

### Backend (FastAPI)
```
app/
├── api/                    # Capa de API REST
│   ├── routers/           # Endpoints por módulo
│   │   ├── descriptions.py # Generación de descripciones
│   │   ├── images.py      # Generación de imágenes
│   │   └── feedback.py    # Análisis de feedback
│   ├── deps.py           # Inyección de dependencias
│   ├── errors.py         # Manejo de errores
│   └── middleware.py     # Middleware de correlación
├── core/                 # Configuración central
│   ├── config.py        # Variables de entorno
│   ├── logging.py       # Sistema de logging
│   └── langsmith.py     # Integración LangSmith
├── domain/              # Lógica de negocio
│   ├── models/          # Modelos Pydantic
│   ├── chains/          # Cadenas LangChain
│   ├── services/        # Servicios de aplicación
│   └── prompts/         # Templates de prompts
├── infra/               # Infraestructura
│   ├── image_providers/ # Proveedores de imágenes
│   └── storage.py       # Almacenamiento de archivos
└── tests/               # Suite de pruebas
```

### Frontend (Gradio)
- **Interfaz web intuitiva** con 3 pestañas principales
- **Formularios interactivos** con validación en tiempo real
- **Visualización de resultados** con formato JSON
- **Descarga automática** de archivos generados

## 🛠️ Tecnologías

- **Backend**: FastAPI, Python 3.11+
- **AI/ML**: LangChain, OpenAI GPT-4o, DALL-E 3
- **Frontend**: Gradio
- **Datos**: Pandas, OpenPyXL
- **Monitoreo**: LangSmith (opcional)
- **Containerización**: Docker, Docker Compose
- **Testing**: Pytest, pytest-asyncio
- **Calidad de código**: Ruff, Black, MyPy, Pre-commit

## 🚀 Instalación y Uso

### Opción 1: Docker Compose (Recomendado)

1. **Clonar el repositorio**:
```bash
git clone <repository-url>
cd poc_healthysnackIA
```

2. **Configurar variables de entorno**:
```bash
cp configs/.env.example configs/.env
```

3. **Editar `configs/.env`** con tu API key de OpenAI:
```bash
OPENAI_API_KEY=tu-api-key-aqui
OPENAI_MODEL=gpt-4o
OPENAI_IMAGE_MODEL=dall-e-3
```

4. **Iniciar los servicios**:
```bash
docker-compose up -d
```

5. **Verificar servicios**:
```bash
curl http://localhost:8000/health      # API health
curl http://localhost:7860            # Frontend
```

### Opción 2: Desarrollo Local

1. **Instalar dependencias**:
```bash
pip install -e ".[dev]"
```

2. **Configurar pre-commit hooks**:
```bash
pre-commit install
```

3. **Configurar variables de entorno**:
```bash
cp configs/.env.example configs/.env
# Editar configs/.env con tus API keys
```

4. **Ejecutar API**:
```bash
python -m app.main
```

5. **Ejecutar Frontend** (en otra terminal):
```bash
python frontend/app.py
```

## 🌐 Acceso a la Aplicación

- **Frontend (Gradio UI)**: http://localhost:7860
  - 📝 **Descripciones**: Genera descripciones de productos
  - 🎨 **Imágenes**: Crea imágenes promocionales
  - 📊 **Análisis**: Analiza feedback de clientes

- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

## 📋 Uso de la API

### Generar Descripciones
```bash
curl -X POST "http://localhost:8000/v1/descriptions/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Almendras Tostadas Orgánicas",
    "channels": ["ecommerce", "social_media"],
    "key_benefits": ["Alto en proteína", "Sin gluten", "Orgánico"]
  }'
```

### Generar Imágenes
```bash
curl -X POST "http://localhost:8000/v1/images/generate" \
  -F "prompt_brief=Almendras tostadas en bowl de madera, estilo natural" \
  -F "aspect_ratio=1:1" \
  -F "cantidad_imagenes=1"
```

### Analizar Feedback
```bash
curl -X POST "http://localhost:8000/v1/feedback/analyze" \
  -F "file=@feedback_comments.csv"
```

## ⚙️ Configuración

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OPENAI_API_KEY` | changeme | API key de OpenAI |
| `OPENAI_MODEL` | gpt-4o | Modelo para generación de texto |
| `OPENAI_IMAGE_MODEL` | dall-e-3 | Modelo para generación de imágenes |
| `LOG_LEVEL` | INFO | Nivel de logging |
| `API_HOST` | 0.0.0.0 | Host de la API |
| `API_PORT` | 8000 | Puerto de la API |
| `FRONTEND_PORT` | 7860 | Puerto del frontend |
| `REQUEST_TIMEOUT_S` | 60 | Timeout de requests |
| `MAX_CONCURRENCY` | 5 | Máximo requests concurrentes |

### LangSmith (Opcional)
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=tu-langsmith-key
LANGCHAIN_PROJECT=tu-proyecto
```

## 🧪 Testing

### Ejecutar todas las pruebas
```bash
pytest
```

### Con cobertura
```bash
pytest --cov=app --cov-report=html
```

### Linting y formateo
```bash
ruff check app/
black app/
mypy app/
```

## 📊 Rendimiento

### Análisis de Feedback
- **Procesamiento concurrente**: ~5-15 comentarios por segundo
- **Tamaño máximo**: 10MB por archivo
- **Formatos soportados**: CSV, XLSX
- **Comentarios recomendados**: Hasta ~1000 para mejor performance

### Generación de Imágenes
- **Tiempo promedio**: 10-30 segundos por imagen
- **Formatos soportados**: PNG (alta resolución)
- **Aspect ratios**: 1:1, 16:9, 9:16, 4:3, 3:4
- **Cantidad máxima**: 3 imágenes por request

## 🔧 Desarrollo

### Estructura de Commits
```bash
git commit -m "feat: nueva funcionalidad"
git commit -m "fix: corrección de bug"
git commit -m "docs: actualización documentación"
```

### Pre-commit Hooks
El proyecto incluye hooks automáticos para:
- Formateo con Black
- Linting con Ruff
- Type checking con MyPy
- Validación de commits

## 📁 Archivos de Configuración

- `configs/brand_guidelines.json`: Guidelines de voz y tono de marca
- `configs/channel_presets.json`: Configuraciones por canal
- `configs/.env.example`: Template de variables de entorno
- `pyproject.toml`: Configuración del proyecto Python
- `docker-compose.yml`: Orquestación de servicios

## 🐳 Docker

### Servicios
- **api**: Backend FastAPI (puerto 8000)
- **frontend**: Interfaz Gradio (puerto 7860)

### Volúmenes
- `./data`: Almacenamiento de artefactos generados
- `./configs`: Archivos de configuración

