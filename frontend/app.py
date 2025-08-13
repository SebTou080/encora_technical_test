"""Gradio frontend for Healthy Snack IA - 3 tabs interface."""

import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import requests

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "7860"))


class SnackIAClient:
    """Client for communicating with the Healthy Snack IA API."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def generate_descriptions(self, **kwargs) -> Dict[str, Any]:
        """Generate product descriptions."""
        try:
            response = self.session.post(
                f"{self.base_url}/v1/descriptions/generate",
                json=kwargs,
                timeout=120
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def generate_image(self, **kwargs) -> Dict[str, Any]:
        """Generate promotional image."""
        try:
            # Prepare multipart data
            files = {}
            data = {}
            
            for key, value in kwargs.items():
                if key == 'reference_image' and value is not None:
                    files['reference_image'] = value
                else:
                    data[key] = value
            
            response = self.session.post(
                f"{self.base_url}/v1/images/generate",
                data=data,
                files=files if files else None,
                timeout=180
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_feedback(self, file_path: str) -> Dict[str, Any]:
        """Analyze feedback from uploaded file."""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = self.session.post(
                    f"{self.base_url}/v1/feedback/analyze",
                    files=files,
                    timeout=300
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def download_artifact(self, job_id: str, filename: str) -> Optional[str]:
        """Download artifact file and return local path."""
        try:
            response = self.session.get(
                f"{self.base_url}/v1/images/artifacts/{job_id}/download/{filename}",
                timeout=60
            )
            response.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp_file:
                tmp_file.write(response.content)
                return tmp_file.name
        except Exception as e:
            print(f"Download failed: {e}")
            return None
    
    def download_feedback_excel(self, job_id: str) -> Optional[str]:
        """Download feedback analysis Excel file."""
        try:
            # First, trigger export
            self.session.post(f"{self.base_url}/v1/feedback/export/{job_id}", timeout=60)
            
            # Then download
            response = self.session.get(
                f"{self.base_url}/v1/feedback/download/{job_id}/feedback_analysis.xlsx",
                timeout=60
            )
            response.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix="_feedback_analysis.xlsx") as tmp_file:
                tmp_file.write(response.content)
                return tmp_file.name
        except Exception as e:
            print(f"Excel export failed: {e}")
            return None


# Global client instance
client = SnackIAClient()


def format_json_display(data: Dict[str, Any]) -> str:
    """Format JSON data for better display in Gradio."""
    return json.dumps(data, indent=2, ensure_ascii=False)


# ========================
# TAB 1: DESCRIPTIONS
# ========================

def show_loading_message() -> str:
    """Show loading message while processing."""
    return """⏳ **Generando descripciones...**

<div style="background-color: #f0f8ff; padding: 15px; border-radius: 10px; border-left: 4px solid #4CAF50;">

🤖 **Procesando tu solicitud** - Esto puede tomar unos momentos

**¿Qué estamos haciendo?**
- 📝 Analizando la información del producto
- 🧠 Generando contenido optimizado con IA (GPT-5-nano)
- 🎯 Adaptando el texto para cada canal solicitado
- 🛡️ Verificando compliance y guardrails de contenido
- ✨ Aplicando el tono de voz seleccionado


Por favor **no recargues la página** mientras nuestro modelo de IA trabaja en tu contenido...

</div>

---

💡 **Tip:** Mientras esperas, puedes revisar que toda la información esté completa para obtener mejores resultados.
"""

def generate_descriptions_interface(
    product_name: str,
    brand: str,
    channels: List[str],
    target_audience: str,
    category: str,
    features: str,
    ingredients: str,
    calories: Optional[int],
    protein_g: Optional[float],
    fat_g: Optional[float],
    carbs_g: Optional[float],
    tone: str
) -> str:
    """Generate product descriptions interface."""
    
    if not product_name or not brand:
        return "❌ **Error**: Nombre del producto y marca son requeridos."
    
    if not channels:
        return "❌ **Error**: Selecciona al menos un canal."
    
    # Prepare request data
    request_data = {
        "product_name": product_name,
        "brand": brand,
        "channels": channels,
        "target_audience": target_audience or "Consumidores conscientes de su salud",
        "category": category,
        "features": [f.strip() for f in features.split(",") if f.strip()],
        "ingredients": [i.strip() for i in ingredients.split(",") if i.strip()],
        "tone": tone
    }
    
    # Add nutrition facts if provided
    nutrition_facts = {}
    if calories is not None:
        nutrition_facts["calories"] = calories
    if protein_g is not None:
        nutrition_facts["protein_g"] = protein_g
    if fat_g is not None:
        nutrition_facts["fat_g"] = fat_g
    if carbs_g is not None:
        nutrition_facts["carbs_g"] = carbs_g
    
    if nutrition_facts:
        request_data["nutrition_facts"] = nutrition_facts
    
    # Generate descriptions
    result = client.generate_descriptions(**request_data)
    
    if "error" in result:
        return f"❌ **Error**: {result['error']}"
    
    # Format beautiful results
    by_channel = result.get('by_channel', {})
    
    formatted_result = f"""✅ **Descripciones generadas exitosamente para {result.get('product_name', 'N/A')}**

"""
    
    # Format each channel nicely
    for channel, content in by_channel.items():
        if channel == 'ecommerce' and content:
            formatted_result += f"""## 🛒 **E-commerce**
**Título**: {content.get('title', 'N/A')}

**Descripción corta**: {content.get('short_description', 'N/A')}

**Descripción larga**: {content.get('long_description', 'N/A')}

**Puntos clave**:
{chr(10).join([f"• {bullet}" for bullet in content.get('bullets', [])])}

---

"""
        
        elif channel == 'mercado_libre' and content:
            formatted_result += f"""## 🟡 **MercadoLibre**
**Título**: {content.get('title', 'N/A')}

**Puntos clave**:
{chr(10).join([f"• {bullet}" for bullet in content.get('bullets', [])])}

---

"""
        
        elif channel == 'instagram' and content:
            formatted_result += f"""## 📸 **Instagram**
**Caption**: {content.get('caption', 'N/A')}

**Hashtags**: {' '.join([f"#{tag}" for tag in content.get('hashtags', [])])}

---

"""
    
    # Add compliance info
    compliance = result.get('compliance', {})
    formatted_result += f"""## 🛡️ **Compliance**
- **Claims de salud detectados**: {len(compliance.get('health_claims', []))}
- **Nivel de lectura**: {compliance.get('reading_level', 'N/A')}
- **Modelo usado**: {result.get('trace', {}).get('model', 'N/A')}
"""
    
    return formatted_result


# ========================
# TAB 2: IMAGES
# ========================

def show_image_loading() -> List[str]:
    """Show image loading placeholder."""
    # Return a placeholder image or empty list while loading
    return []

def generate_image_interface(
    prompt_brief: str,
    aspect_ratio: str,
    cantidad_imagenes: int
) -> Optional[List[str]]:
    """Generate promotional images interface."""
    
    if not prompt_brief:
        return None
    
    # Prepare request data
    request_data = {
        "prompt_brief": prompt_brief,
        "aspect_ratio": aspect_ratio,
        "cantidad_imagenes": cantidad_imagenes
    }
    
    # Generate images
    result = client.generate_image(**request_data)
    
    if "error" in result:
        return None
    
    # Download generated images
    job_id = result.get("job_id")
    if job_id:
        image_paths = []
        for i in range(cantidad_imagenes):
            filename = f"image_{i + 1}.png"
            image_path = client.download_artifact(job_id, filename)
            if image_path:
                image_paths.append(image_path)
        
        if image_paths:
            return image_paths
    
    return None


# ========================
# TAB 3: FEEDBACK
# ========================

def show_feedback_loading() -> Tuple[str, str]:
    """Show feedback analysis loading message."""
    loading_msg = """⏳ **Analizando feedback...**

🤖 **Procesando tu archivo** - Esto puede tomar unos momentos

**¿Qué estamos haciendo?**
- 📄 Leyendo y parseando tu archivo
- 🧠 Analizando sentimientos con IA
- 🏷️ Identificando temas principales
- ⚠️ Detectando issues y problemas
- 💡 Extrayendo feature requests
- 📊 Generando insights y estadísticas

**⏱️ Tiempo estimado:** 1-3 minutos dependiendo del tamaño del archivo

Por favor espera mientras analizamos todos los comentarios...
"""
    return loading_msg, ""

def analyze_feedback_interface(file) -> Tuple[str, str]:
    """Analyze feedback from uploaded file interface."""
    
    if file is None:
        return "❌ Error: Selecciona un archivo CSV o XLSX.", ""
    
    # Analyze feedback
    result = client.analyze_feedback(file.name)
    
    if "error" in result:
        return f"❌ Error: {result['error']}", ""
    
    # Extract insights for summary
    overall_sentiment = result.get("overall_sentiment", {})
    themes = result.get("themes", [])
    issues = result.get("top_issues", [])
    requests = result.get("feature_requests", [])
    highlights = result.get("highlights", [])
    
    # Format success message with insights
    success_msg = f"""✅ **Análisis de feedback completado**

**Sentimiento General**: {overall_sentiment.get('label', 'N/A').title()} ({overall_sentiment.get('score', 0):.2f})

**📊 Resumen de Insights**:
- **Temas identificados**: {len(themes)}
- **Issues encontrados**: {len(issues)}
- **Feature requests**: {len(requests)}
- **Highlights**: {len(highlights)}

**🔍 Top Temas**:
{chr(10).join([f"- {theme.get('name', 'N/A')}" for theme in themes[:5]])}

**⚠️ Issues Principales**:
{chr(10).join([f"- {issue.get('issue', 'N/A')} (Prioridad: {issue.get('priority', 'N/A')})" for issue in issues[:3]])}

**💡 Feature Requests**:
{chr(10).join([f"- {req.get('request', 'N/A')} ({req.get('count', 0)} menciones)" for req in requests[:3]])}
"""
    
    json_result = format_json_display(result)
    return success_msg, json_result


# ========================
# GRADIO INTERFACE
# ========================

def create_gradio_interface():
    """Create the main Gradio interface with 3 tabs."""
    
    with gr.Blocks(
        title="Healthy Snack IA",
        theme=gr.themes.Soft()
    ) as app:
        
        gr.Markdown(
            """
            # 🥗 Healthy Snack IA
            ### Plataforma completa para marketing de snacks saludables
            
            **Funcionalidades:**
            - 📝 **Descripciones**: Genera content optimizado por canal
            - 🎨 **Imágenes**: Crea imágenes promocionales con IA  
            - 📊 **Feedback**: Analiza comentarios de usuarios
            """
        )
        
        
        with gr.Tabs():
            
            # ============================================
            # TAB 1: DESCRIPTIONS
            # ============================================
            with gr.Tab("📝 Descripciones"):
                gr.Markdown("### Genera descripciones optimizadas por canal")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 🏷️ Información del Producto")
                        product_name = gr.Textbox(
                            label="Nombre del Producto",
                            placeholder="Ej: Chips de Kale al Horno",
                            value=""
                        )
                        
                        brand = gr.Textbox(
                            label="Marca", 
                            placeholder="GreenBite", 
                            value=""
                        )
                        
                        category = gr.Textbox(
                            label="Categoría",
                            placeholder="snacks_saludables",
                            value="snacks_saludables"
                        )
                        
                        channels = gr.CheckboxGroup(
                            choices=["ecommerce", "mercado_libre", "instagram"],
                            label="Canales de Marketing",
                            value=["ecommerce"]
                        )
                        
                        target_audience = gr.Textbox(
                            label="Público Objetivo",
                            placeholder="adultos conscientes de su salud",
                            value=""
                        )
                        
                    with gr.Column():
                        gr.Markdown("#### 🎯 Detalles del Producto")
                        features = gr.Textbox(
                            label="Características (separadas por comas)",
                            placeholder="horneado, sin fritura, vegano, sin gluten",
                            value=""
                        )
                        
                        ingredients = gr.Textbox(
                            label="Ingredientes (separados por comas)",
                            placeholder="kale, aceite de oliva, sal marina",
                            value=""
                        )
                        
                        gr.Markdown("#### 🥗 Información Nutricional (opcional)")
                        with gr.Row():
                            calories = gr.Number(label="Calorías", minimum=0, maximum=1000)
                            protein_g = gr.Number(label="Proteína (g)", minimum=0, maximum=100)
                        
                        with gr.Row():
                            fat_g = gr.Number(label="Grasa (g)", minimum=0, maximum=100)
                            carbs_g = gr.Number(label="Carbohidratos (g)", minimum=0, maximum=100)
                        
                        gr.Markdown("#### ✨ Configuración")
                        tone = gr.Dropdown(
                            choices=[
                                "cálido y experto",
                                "profesional y técnico", 
                                "friendly y casual",
                                "premium y sofisticado"
                            ],
                            value="cálido y experto",
                            label="Tono de Voz"
                        )
                        
                        
                        generate_desc_btn = gr.Button(
                            "🚀 Generar Descripciones", 
                            variant="primary",
                            elem_id="generate-desc-btn"
                        )
                
                desc_results = gr.Markdown(
                    label="Resultados",
                    show_label=True
                )
                
                # Event handler for descriptions
                def handle_generate_descriptions(*args):
                    """Handle description generation with loading state."""
                    # Show loading message immediately
                    yield show_loading_message()
                    # Generate actual descriptions
                    result = generate_descriptions_interface(*args)
                    yield result
                
                generate_desc_btn.click(
                    fn=handle_generate_descriptions,
                    inputs=[
                        product_name, brand, channels,
                        target_audience, category, features, ingredients,
                        calories, protein_g, fat_g, carbs_g, tone
                    ],
                    outputs=[desc_results],
                    show_progress="full"  # Shows progress bar
                )
            
            # ============================================
            # TAB 2: IMAGES
            # ============================================
            with gr.Tab("🎨 Imágenes"):
                gr.Markdown("### Genera imágenes promocionales con IA")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 🖼️ Configuración de Imagen")
                        prompt_brief = gr.Textbox(
                            label="Prompt de la Imagen",
                            placeholder="Chips de Kale crujientes sobre superficie de madera clara con ingredientes frescos",
                            lines=3,
                            value=""
                        )
                        
                        
                        aspect_ratio = gr.Dropdown(
                            choices=["1:1", "16:9", "9:16", "4:3", "3:4"],
                            value="1:1",
                            label="Proporción de Aspecto"
                        )
                        
                        cantidad_imagenes = gr.Dropdown(
                             choices=[1, 2, 3],
                             value=1,
                             label="Cantidad de Imágenes"
                         )
                        
                        generate_img_btn = gr.Button(
                            "🎨 Generar Imágenes", 
                            variant="primary",
                            elem_id="generate-img-btn"
                        )
                    
                    with gr.Column():
                        gr.Markdown("#### 🖼️ Imágenes Generadas")
                        generated_images = gr.Gallery(
                            label="Resultados",
                            show_label=True,
                            columns=2,
                            rows=2,
                            height="auto"
                        )
                
                
                # Event handler for images
                def handle_generate_images(*args):
                    """Handle image generation with loading state."""
                    # Show empty gallery while loading
                    yield []
                    # Generate actual images
                    result = generate_image_interface(*args)
                    yield result if result is not None else []
                
                generate_img_btn.click(
                    fn=handle_generate_images,
                    inputs=[prompt_brief, aspect_ratio, cantidad_imagenes],
                    outputs=[generated_images],
                    show_progress="full"  # Shows progress bar
                )
            
            # ============================================
            # TAB 3: FEEDBACK
            # ============================================
            with gr.Tab("📊 Análisis de Feedback"):
                gr.Markdown("### Analiza comentarios y feedback de usuarios")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 📄 Upload de Archivo")
                        
                        feedback_file = gr.File(
                            label="Archivo de Comentarios",
                            file_types=[".csv", ".xlsx", ".xls"],
                            file_count="single"
                        )
                        
                        gr.Markdown(
                            """
                            **Formato esperado:**
                            - **Columna requerida**: `comment` (con el texto del comentario)
                            - **Columnas opcionales**: `username`, `channel`, `date`
                            - **Formatos**: CSV (UTF-8) o Excel
                            - **Tamaño máximo**: 10MB
                            
                            **Ejemplo CSV:**
                            ```
                            comment,username,channel
                            "Me encantan estos chips",user1,ecommerce
                            "Muy caros pero ricos",user2,instagram
                            ```
                            """
                        )
                        
                        analyze_btn = gr.Button(
                            "🔍 Analizar Feedback", 
                            variant="primary",
                            elem_id="analyze-btn"
                        )
                    
                    with gr.Column():
                        gr.Markdown("#### 📊 Insights Generados")
                        feedback_insights = gr.Textbox(
                            label="Resumen de Insights",
                            interactive=False,
                            max_lines=15
                        )
                        
                
                with gr.Row():
                    feedback_results = gr.JSON(
                        label="Resultados Detallados del Análisis",
                        show_label=True
                    )
                
                # Event handler for feedback
                def handle_analyze_feedback(file):
                    """Handle feedback analysis with loading state."""
                    # Show loading message immediately
                    yield show_feedback_loading()
                    # Analyze actual feedback
                    insights, results = analyze_feedback_interface(file)
                    yield insights, results
                
                analyze_btn.click(
                    fn=handle_analyze_feedback,
                    inputs=[feedback_file],
                    outputs=[feedback_insights, feedback_results],
                    show_progress="full"  # Shows progress bar
                )
        
    
    return app


# ========================
# MAIN APPLICATION
# ========================

if __name__ == "__main__":
    # Create and launch the Gradio interface
    app = create_gradio_interface()
    
    # Launch Gradio app with minimal, widely supported parameters for compatibility
    app.launch(
        server_name="0.0.0.0",
        server_port=FRONTEND_PORT
    )