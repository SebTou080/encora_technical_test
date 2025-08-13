"""Storage service for artifacts and generated content."""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..core.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """Service for managing file storage and artifacts."""

    def __init__(self, base_path: str = "./data") -> None:
        """Initialize storage service with base path."""
        self.base_path = Path(base_path)
        self.artifacts_path = self.base_path / "artifacts"

        # Ensure directories exist
        self.artifacts_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Storage initialized at: {self.base_path.absolute()}")

    def create_job_directory(self, job_id: str | None = None) -> str:
        """Create a new directory for a job and return the job ID."""
        if not job_id:
            job_id = str(uuid4())

        job_dir = self.artifacts_path / job_id
        job_dir.mkdir(exist_ok=True)

        logger.info(f"📂 Created job directory: {job_id}")
        return job_id

    def save_image(
        self, job_id: str, image_bytes: bytes, filename: str = "image.png"
    ) -> str:
        """Save image bytes to job directory."""
        job_dir = self.artifacts_path / job_id
        image_path = job_dir / filename

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        relative_path = f"./data/artifacts/{job_id}/{filename}"
        logger.info(f"💾 Saved image: {relative_path} ({len(image_bytes)} bytes)")
        return relative_path

    def save_metadata(
        self, job_id: str, metadata: dict[str, Any], filename: str = "metadata.json"
    ) -> str:
        """Save metadata to job directory."""
        job_dir = self.artifacts_path / job_id
        metadata_path = job_dir / filename

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        relative_path = f"./data/artifacts/{job_id}/{filename}"
        logger.info(f"📝 Saved metadata: {relative_path}")
        return relative_path

    def load_metadata(
        self, job_id: str, filename: str = "metadata.json"
    ) -> dict[str, Any] | None:
        """Load metadata from job directory."""
        try:
            metadata_path = self.artifacts_path / job_id / filename

            if not metadata_path.exists():
                return None

            with open(metadata_path, encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"❌ Failed to load metadata for {job_id}: {e}")
            return None

    def get_artifact_path(self, job_id: str, filename: str) -> str | None:
        """Get full path to an artifact file."""
        artifact_path = self.artifacts_path / job_id / filename

        if artifact_path.exists():
            return str(artifact_path.absolute())

        return None

    def list_job_artifacts(self, job_id: str) -> list[str]:
        """List all artifacts in a job directory."""
        try:
            job_dir = self.artifacts_path / job_id

            if not job_dir.exists():
                return []

            return [f.name for f in job_dir.iterdir() if f.is_file()]

        except Exception as e:
            logger.error(f"❌ Failed to list artifacts for {job_id}: {e}")
            return []

    def cleanup_old_artifacts(self, days_old: int = 7) -> None:
        """Clean up artifacts older than specified days."""
        import time

        try:
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 60 * 60)
            removed_count = 0

            for job_dir in self.artifacts_path.iterdir():
                if job_dir.is_dir():
                    dir_mtime = job_dir.stat().st_mtime
                    if dir_mtime < cutoff_time:
                        import shutil

                        shutil.rmtree(job_dir)
                        removed_count += 1

            if removed_count > 0:
                logger.info(f"🧹 Cleaned up {removed_count} old artifact directories")

        except Exception as e:
            logger.error(f"❌ Failed to cleanup old artifacts: {e}")

    def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        try:
            total_size = 0
            total_files = 0
            job_count = 0

            for job_dir in self.artifacts_path.iterdir():
                if job_dir.is_dir():
                    job_count += 1
                    for file_path in job_dir.rglob("*"):
                        if file_path.is_file():
                            total_files += 1
                            total_size += file_path.stat().st_size

            return {
                "total_jobs": job_count,
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "storage_path": str(self.base_path.absolute()),
            }

        except Exception as e:
            logger.error(f"❌ Failed to get storage stats: {e}")
            return {"error": str(e)}


# Global storage instance
storage = StorageService()
