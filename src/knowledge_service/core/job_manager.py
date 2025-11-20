"""Job tracking and management for async operations."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class Job:
    """Represents an asynchronous job."""

    def __init__(self, job_id: str, job_type: str):
        self.job_id = job_id
        self.job_type = job_type
        self.status = "pending"  # pending, processing, completed, failed
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.progress: Optional[float] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

    def update_status(self, status: str, progress: Optional[float] = None,
                     result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Update job status and metadata."""
        self.status = status
        self.updated_at = datetime.utcnow()
        if progress is not None:
            self.progress = progress
        if result is not None:
            self.result = result
        if error is not None:
            self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "result": self.result,
            "error": self.error
        }


class JobManager:
    """Manager for tracking async jobs."""

    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_job(self, job_type: str) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid4())
        job = Job(job_id, job_type)
        self.jobs[job_id] = job
        logger.info(f"Created job {job_id} of type {job_type}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self.jobs.get(job_id)

    def update_job(self, job_id: str, status: str, progress: Optional[float] = None,
                   result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Update job status."""
        job = self.jobs.get(job_id)
        if job:
            job.update_status(status, progress, result, error)
            logger.info(f"Updated job {job_id} to status {status}")
        else:
            logger.warning(f"Job {job_id} not found for update")

    def delete_job(self, job_id: str):
        """Delete a job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"Deleted job {job_id}")

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up jobs older than specified hours."""
        now = datetime.utcnow()
        to_delete = []

        for job_id, job in self.jobs.items():
            age_hours = (now - job.created_at).total_seconds() / 3600
            if age_hours > max_age_hours and job.status in ["completed", "failed"]:
                to_delete.append(job_id)

        for job_id in to_delete:
            self.delete_job(job_id)

        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old jobs")

    async def start_cleanup_task(self, interval_minutes: int = 60):
        """Start background task to clean up old jobs."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_minutes * 60)
                await self.cleanup_old_jobs()

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started job cleanup background task")

    async def stop_cleanup_task(self):
        """Stop the cleanup background task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped job cleanup background task")
