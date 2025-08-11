# Sistema de Análisis de Comentarios y Feedback

## Objetivos del Análisis
- Extraer insights accionables de comentarios de usuarios
- Identificar patrones de satisfacción e insatisfacción
- Priorizar issues y feature requests por impacto
- Generar recommendations estratégicas basadas en datos

## Categorías de Análisis

### 1. Análisis de Sentimiento
**Niveles:**
- `positive`: Comentarios favorables, satisfacción, recomendaciones
- `neutral`: Comentarios informativos, consultas, feedback constructivo
- `negative`: Quejas, problemas, insatisfacción

**Criterios:**
- **Positive**: "me encanta", "delicioso", "perfecto", "recomiendo"
- **Neutral**: "está bien", "normal", "consulta sobre", "¿cómo?"
- **Negative**: "malo", "horrible", "decepcionante", "no me gustó"

### 2. Temas Principales
**Categorías identificadas:**
- **sabor**: gustos, palatabilidad, comparaciones de sabor
- **textura**: crujiente, suave, consistencia, frescura
- **empaque**: envoltorio, presentación, tamaño, conservación
- **precio**: costo, relación precio-calidad, ofertas
- **disponibilidad**: dónde comprar, stock, distribución
- **salud**: beneficios nutricionales, ingredientes, alergias
- **tamaño_porcion**: cantidad por paquete, saciedad
- **comparacion**: vs otros productos, marcas competidoras

### 3. Issues Prioritarios
**Niveles de prioridad:**
- **alta**: Afecta experiencia principal del producto (sabor, frescura, seguridad)
- **media**: Afecta conveniencia o satisfacción (empaque, precio, disponibilidad)  
- **baja**: Mejoras deseables pero no críticas (variedad, presentación)

### 4. Feature Requests
**Tipos comunes:**
- **nuevos_sabores**: Solicitudes de variantes de sabor
- **formato_familiar**: Paquetes más grandes para familia
- **version_organica**: Versión certificada orgánica
- **sin_sal**: Versión baja en sodio
- **empaque_reciclable**: Packaging sustentable
- **mix_sabores**: Paquetes combinados

## Directrices de Análisis

### Para Sentiment Analysis
```
Analiza el sentimiento del siguiente comentario sobre snacks saludables.
Considera el contexto, ironía, y matices emocionales.
Clasifica como: positive, neutral, o negative
Proporciona score de confianza (0.0-1.0)

Comentario: "{comment}"
```

### Para Extracción de Temas
```
Identifica los temas principales mencionados en este comentario.
Enfócate en aspectos del producto: sabor, textura, empaque, precio, salud, disponibilidad.
Lista máximo 3 temas más relevantes.

Comentario: "{comment}"
```

### Para Identificación de Issues
```
¿Este comentario menciona algún problema o issue con el producto?
Si es así, clasifica la severidad como: alta, media, baja
Describe el issue específico en 1-2 palabras clave.

Comentario: "{comment}"
```

## Agregaciones y Métricas

### Por SKU
- Distribución de sentiment por producto
- Temas más mencionados por SKU
- Issues específicos recurrentes
- Score promedio de satisfacción

### Por Canal
- Diferencias de sentiment entre canales (ecommerce, redes sociales)
- Temas prioritarios por plataforma
- Volumen de feedback por canal

### Temporal
- Evolución de sentiment en el tiempo
- Identificación de tendencias emergentes
- Impacto de lanzamientos en feedback

## Salidas Esperadas

### Highlights (Quotes Notables)
- Testimoniales positivos para marketing
- Críticas constructivas específicas
- Feature requests con mayor demanda

### Recommendations
- Acciones inmediatas basadas en issues alta prioridad
- Oportunidades de producto basadas en requests
- Estrategias de comunicación por canal