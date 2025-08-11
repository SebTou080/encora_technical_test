"""Gradio frontend for Healthy Snack IA - 3 tabs interface."""

import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import pandas as pd
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

def generate_descriptions_interface(
    product_name: str,
    sku: str,
    brand: str,
    language: str,
    channels: List[str],
    target_audience: str,
    category: str,
    features: str,
    ingredients: str,
    calories: Optional[int],
    protein_g: Optional[float],
    fat_g: Optional[float],
    carbs_g: Optional[float],
    tone: str,
    variants: int
) -> Tuple[str, str]:
    """Generate product descriptions interface."""
    
    if not product_name or not sku or not brand:
        return "❌ Error: Nombre del producto, SKU y marca son requeridos.", ""
    
    if not channels:
        return "❌ Error: Selecciona al menos un canal.", ""
    
    # Prepare request data
    request_data = {
        "product_name": product_name,
        "sku": sku,
        "brand": brand,
        "language": language,
        "channels": channels,
        "target_audience": target_audience or "Consumidores conscientes de su salud",
        "category": category,
        "features": [f.strip() for f in features.split(",") if f.strip()],
        "ingredients": [i.strip() for i in ingredients.split(",") if i.strip()],
        "tone": tone,
        "variants": variants
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
        return f"❌ Error: {result['error']}", ""
    
    # Format success response
    success_msg = f"""✅ **Descripciones generadas exitosamente**

**SKU**: {result.get('sku', 'N/A')}
**Idioma**: {result.get('language', 'N/A')}
**Modelo usado**: {result.get('trace', {}).get('model', 'N/A')}

**Compliance**:
- Claims de salud: {len(result.get('compliance', {}).get('health_claims', []))}
- Nivel de lectura: {result.get('compliance', {}).get('reading_level', 'N/A')}
"""
    
    # Format detailed results
    json_result = format_json_display(result)
    
    return success_msg, json_result


# ========================
# TAB 2: IMAGES
# ========================

def generate_image_interface(
    prompt_brief: str,
    brand_style: str,
    aspect_ratio: str,
    seed: Optional[int],
    reference_image
) -> Tuple[str, str, Optional[str]]:
    """Generate promotional image interface."""
    
    if not prompt_brief:
        return "❌ Error: Prompt de la imagen es requerido.", "", None
    
    # Prepare request data
    request_data = {
        "prompt_brief": prompt_brief,
        "aspect_ratio": aspect_ratio
    }
    
    if brand_style:
        request_data["brand_style"] = brand_style
    
    if seed is not None:
        request_data["seed"] = seed
    
    if reference_image is not None:
        request_data["reference_image"] = reference_image
    
    # Generate image
    result = client.generate_image(**request_data)
    
    if "error" in result:
        return f"❌ Error: {result['error']}", "", None
    
    # Download generated image
    job_id = result.get("job_id")
    if job_id:
        image_path = client.download_artifact(job_id, "image.png")
        if image_path:
            success_msg = f"""✅ **Imagen generada exitosamente**

**Job ID**: {job_id}
**Dimensiones**: {result.get('width')}x{result.get('height')}
**Proveedor**: {result.get('provider', 'N/A')}
**Modelo**: {result.get('model_url', 'N/A').split('/')[-1]}

**Metadata**:
- Prompt optimizado: ✅
- Seed: {result.get('meta', {}).get('seed', 'N/A')}
- Tamaño archivo: {result.get('meta', {}).get('file_size_bytes', 0)} bytes
"""
            
            json_result = format_json_display(result)
            return success_msg, json_result, image_path
    
    return "⚠️ Imagen generada pero no se pudo descargar.", format_json_display(result), None


# ========================
# TAB 3: FEEDBACK
# ========================

def analyze_feedback_interface(file) -> Tuple[str, str, Optional[str]]:
    """Analyze feedback from uploaded file interface."""
    
    if file is None:
        return "❌ Error: Selecciona un archivo CSV o XLSX.", "", None
    
    # Analyze feedback
    result = client.analyze_feedback(file.name)
    
    if "error" in result:
        return f"❌ Error: {result['error']}", "", None
    
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
    
    # Try to get Excel export (we would need job_id tracking for this)
    excel_path = None
    # For now, we'll skip Excel download as it requires job_id tracking
    
    json_result = format_json_display(result)
    return success_msg, json_result, excel_path


# ========================
# GRADIO INTERFACE
# ========================

def create_gradio_interface():
    """Create the main Gradio interface with 3 tabs."""
    
    # Check API health
    health = client.health_check()
    api_status = "✅ API Conectada" if health.get("status") == "healthy" else f"❌ API Error: {health.get('error', 'Unknown')}"
    
    with gr.Blocks(
        title="Healthy Snack IA",
        theme=gr.themes.Soft(),
        css="""
        .status-indicator { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .api-healthy { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .api-error { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        """
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
        
        gr.HTML(f'<div class="status-indicator {"api-healthy" if "✅" in api_status else "api-error"}">{api_status}</div>')
        
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
                        
                        with gr.Row():
                            sku = gr.Textbox(label="SKU", placeholder="KALE-90G", value="")
                            brand = gr.Textbox(label="Marca", placeholder="GreenBite", value="")
                        
                        with gr.Row():
                            language = gr.Dropdown(
                                choices=["es", "en"],
                                value="es",
                                label="Idioma"
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
                        
                        variants = gr.Slider(
                            minimum=1,
                            maximum=3,
                            step=1,
                            value=1,
                            label="Variantes a Generar"
                        )
                        
                        generate_desc_btn = gr.Button("🚀 Generar Descripciones", variant="primary")
                
                with gr.Row():
                    desc_status = gr.Textbox(
                        label="Estado",
                        interactive=False,
                        max_lines=10
                    )
                    
                    desc_results = gr.JSON(
                        label="Resultados Detallados",
                        show_label=True
                    )
                
                # Event handler for descriptions
                generate_desc_btn.click(
                    fn=generate_descriptions_interface,
                    inputs=[
                        product_name, sku, brand, language, channels,
                        target_audience, category, features, ingredients,
                        calories, protein_g, fat_g, carbs_g, tone, variants
                    ],
                    outputs=[desc_status, desc_results]
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
                        
                        brand_style = gr.Textbox(
                            label="Estilo de Marca (opcional)",
                            placeholder='{"colors": ["verde natural", "blanco"], "style": "organic premium"}',
                            lines=2,
                            value=""
                        )
                        
                        aspect_ratio = gr.Dropdown(
                            choices=["1:1", "16:9", "9:16", "4:3", "3:4"],
                            value="1:1",
                            label="Proporción de Aspecto"
                        )
                        
                        seed = gr.Number(
                            label="Seed (opcional, para reproducibilidad)",
                            minimum=0,
                            maximum=2147483647,
                            step=1
                        )
                        
                        reference_image = gr.File(
                            label="Imagen de Referencia (opcional)",
                            file_types=["image"]
                        )
                        
                        generate_img_btn = gr.Button("🎨 Generar Imagen", variant="primary")
                    
                    with gr.Column():
                        gr.Markdown("#### 🖼️ Imagen Generada")
                        generated_image = gr.Image(
                            label="Resultado",
                            show_label=True,
                            interactive=False
                        )
                
                with gr.Row():
                    img_status = gr.Textbox(
                        label="Estado",
                        interactive=False,
                        max_lines=8
                    )
                    
                    img_results = gr.JSON(
                        label="Metadatos de Generación",
                        show_label=True
                    )
                
                # Event handler for images
                generate_img_btn.click(
                    fn=generate_image_interface,
                    inputs=[prompt_brief, brand_style, aspect_ratio, seed, reference_image],
                    outputs=[img_status, img_results, generated_image]
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
                            - **Columnas opcionales**: `username`, `sku`, `channel`, `date`
                            - **Formatos**: CSV (UTF-8) o Excel
                            - **Tamaño máximo**: 10MB
                            
                            **Ejemplo CSV:**
                            ```
                            comment,username,sku,channel
                            "Me encantan estos chips",user1,KALE-90G,ecommerce
                            "Muy caros pero ricos",user2,QUINOA-80G,instagram
                            ```
                            """
                        )
                        
                        analyze_btn = gr.Button("🔍 Analizar Feedback", variant="primary")
                    
                    with gr.Column():
                        gr.Markdown("#### 📊 Insights Generados")
                        feedback_insights = gr.Textbox(
                            label="Resumen de Insights",
                            interactive=False,
                            max_lines=15
                        )
                        
                        excel_download = gr.File(
                            label="Descargar Análisis Completo (Excel)",
                            visible=False
                        )
                
                with gr.Row():
                    feedback_results = gr.JSON(
                        label="Resultados Detallados del Análisis",
                        show_label=True
                    )
                
                # Event handler for feedback
                analyze_btn.click(
                    fn=analyze_feedback_interface,
                    inputs=[feedback_file],
                    outputs=[feedback_insights, feedback_results, excel_download]
                )
        
        gr.Markdown(
            """
            ---
            
            ### 🚀 Healthy Snack IA v1.0
            
            **Tecnologías**: FastAPI + LangChain + OpenAI GPT-4o + Hugging Face + Gradio
            
            **Funcionalidades Completas**:
            - ✅ Generación de descripciones multicanal
            - ✅ Creación de imágenes promocionales  
            - ✅ Análisis inteligente de feedback
            - ✅ Exportación y descarga de resultados
            """
        )
    
    return app


# ========================
# MAIN APPLICATION
# ========================

if __name__ == "__main__":
    # Create and launch the Gradio interface
    app = create_gradio_interface()
    
    app.launch(
        server_name="0.0.0.0",
        server_port=FRONTEND_PORT,
        share=False,
        show_error=True,
        show_tips=False,
        enable_queue=True,
        max_threads=10
    )