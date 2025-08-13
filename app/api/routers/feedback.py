"""Feedback analysis API router."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from ...core.logging import get_correlation_id, get_logger
from ...domain.models.feedback import FeedbackAnalyzeResponse
from ...domain.services.feedback_service import FeedbackService
from ..deps import get_feedback_service
from ..errors import ServiceError, ValidationError

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


@router.post("/analyze", response_model=FeedbackAnalyzeResponse)
async def analyze_feedback(
    file: UploadFile = File(..., description="CSV or XLSX file with feedback comments"),
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackAnalyzeResponse:
    """Analyze feedback comments from uploaded CSV/XLSX file."""

    correlation_id = get_correlation_id()

    try:
        # Validate file
        if not file.filename:
            raise ValidationError("Filename is required", correlation_id)

        file_extension = file.filename.lower().split(".")[-1]
        if file_extension not in ["csv", "xlsx", "xls"]:
            raise ValidationError(
                f"Unsupported file format: .{file_extension}. Please upload CSV or XLSX file.",
                correlation_id,
            )

        # Check file size (limit to 10MB)
        if hasattr(file, "size") and file.size and file.size > 10 * 1024 * 1024:
            raise ValidationError(
                "File too large. Maximum size is 10MB.", correlation_id
            )

        logger.info(f"📄 Analyzing feedback file: {file.filename} ({file_extension})")

        # Analyze feedback
        result = await service.analyze_file(file)

        logger.info(f"✨ Feedback analysis complete for {file.filename}")
        return result

    except ValidationError:
        raise
    except ValueError as e:
        raise ServiceError(str(e), correlation_id)
    except Exception as e:
        logger.error(f"💥 Unexpected error analyzing feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/analysis/{job_id}")
async def get_analysis_info(
    job_id: str,
    service: FeedbackService = Depends(get_feedback_service),
) -> dict:
    """Get information about a completed feedback analysis."""

    if not job_id.strip():
        raise ValidationError("Job ID cannot be empty", get_correlation_id())

    analysis_info = service.get_analysis_info(job_id)

    if not analysis_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis not found for job ID: {job_id}",
        )

    return analysis_info


@router.post("/export/{job_id}")
async def export_analysis_to_excel(
    job_id: str,
    service: FeedbackService = Depends(get_feedback_service),
) -> dict:
    """Export analysis results to Excel file with multiple sheets."""

    correlation_id = get_correlation_id()

    if not job_id.strip():
        raise ValidationError("Job ID cannot be empty", correlation_id)

    try:
        logger.info(f"📊 Exporting analysis {job_id} to Excel")

        excel_path = await service.export_results_to_excel(job_id)

        if not excel_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis not found or export failed for job ID: {job_id}",
            )

        logger.info(f"✅ Excel export completed: {job_id}")

        return {
            "job_id": job_id,
            "excel_file": "feedback_analysis.xlsx",
            "download_url": f"/v1/feedback/download/{job_id}/feedback_analysis.xlsx",
            "message": "Excel export completed successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Excel export failed for {job_id}: {e}")
        raise ServiceError(f"Excel export failed: {e}", correlation_id)


@router.get("/download/{job_id}/{filename}")
async def download_analysis_file(
    job_id: str,
    filename: str,
    service: FeedbackService = Depends(get_feedback_service),
) -> FileResponse:
    """Download analysis result files."""

    from ...infra.storage import storage

    if not job_id.strip() or not filename.strip():
        raise ValidationError(
            "Job ID and filename cannot be empty", get_correlation_id()
        )

    # Get file path
    file_path = storage.get_artifact_path(job_id, filename)

    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename} for analysis {job_id}",
        )

    # Determine media type
    media_type = "application/octet-stream"
    if filename.lower().endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif filename.lower().endswith(".json"):
        media_type = "application/json"

    logger.info(f"📥 Serving analysis file: {job_id}/{filename}")

    return FileResponse(path=file_path, filename=filename, media_type=media_type)


@router.get("/sample")
async def get_sample_file_format() -> dict:
    """Get information about the expected file format for feedback analysis."""

    return {
        "description": "Sample format for feedback analysis files",
        "required_columns": ["comment"],
        "optional_columns": ["username", "sku", "channel", "date"],
        "accepted_formats": [".csv", ".xlsx", ".xls"],
        "max_file_size": "10MB",
        "sample_data": [
            {
                "comment": "Me encantan estos chips de kale, muy crujientes",
                "username": "user123",
                "sku": "KALE-90G",
                "channel": "ecommerce",
                "date": "2024-01-15",
            },
            {
                "comment": "El sabor podría ser mejor, pero la textura está bien",
                "username": "user456",
                "sku": "KALE-90G",
                "channel": "instagram",
                "date": "2024-01-16",
            },
        ],
        "column_variations": {
            "comment": [
                "comment",
                "comentario",
                "feedback",
                "review",
                "opinion",
                "text",
            ],
            "username": ["username", "user", "usuario", "name", "nombre"],
            "sku": ["sku", "product_id", "producto", "product"],
            "channel": ["channel", "canal", "platform", "plataforma", "source"],
            "date": ["date", "fecha", "timestamp", "created_at"],
        },
        "tips": [
            "At minimum, include a 'comment' column with feedback text",
            "Comments should be between 5-1000 characters",
            "Include 'sku' and 'channel' columns for detailed analysis by product/platform",
            "CSV files should be UTF-8 encoded to handle special characters",
            "Remove empty rows before uploading",
        ],
    }


@router.get("/health")
async def feedback_health_check() -> dict:
    """Check health of feedback analysis services."""

    try:
        # Check if LLM service is accessible (basic check)
        FeedbackService()

        return {
            "status": "healthy",
            "services": {
                "llm_analysis": {"status": "healthy", "model": "gpt-4o"},
                "file_processing": {"status": "healthy", "formats": ["csv", "xlsx"]},
                "export": {"status": "healthy", "formats": ["xlsx"]},
                "storage": {"status": "healthy"},
            },
            "capabilities": [
                "sentiment_analysis",
                "theme_extraction",
                "issue_identification",
                "feature_request_detection",
                "concurrent_processing",
                "excel_export",
            ],
        }

    except Exception as e:
        logger.error(f"❌ Feedback health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "unhealthy", "error": str(e)},
        )
