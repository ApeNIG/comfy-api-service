"""
Job repository with custom queries
"""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from apps.creator.models.domain import Job
from apps.creator.repositories.base import BaseRepository
from apps.shared.models.enums import JobStatus


class JobRepository(BaseRepository[Job]):
    """
    Job-specific data access operations.

    Inherits standard CRUD from BaseRepository.
    """

    def __init__(self, db: Session):
        super().__init__(db, Job)

    def find_by_user_id(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: JobStatus | None = None,
    ) -> list[Job]:
        """
        Find jobs for a specific user.

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Max records to return
            status: Optional status filter

        Returns:
            List of user's jobs
        """
        query = self.db.query(Job).filter(Job.user_id == user_id)

        if status:
            query = query.filter(Job.status == status.value)

        return (
            query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
        )

    def find_by_status(
        self,
        status: JobStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """
        Find jobs by status.

        Args:
            status: Job status
            skip: Number of records to skip
            limit: Max records to return

        Returns:
            List of jobs with given status
        """
        return (
            self.db.query(Job)
            .filter(Job.status == status.value)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def find_next_queued_job(self) -> Optional[Job]:
        """
        Get next job from queue (FIFO).

        Used by workers to pick up next job.

        Returns:
            Next queued job or None
        """
        return (
            self.db.query(Job)
            .filter(Job.status == JobStatus.QUEUED.value)
            .order_by(Job.queued_at.asc())
            .first()
        )

    def find_stale_processing_jobs(self, timeout_minutes: int = 30) -> list[Job]:
        """
        Find jobs stuck in PROCESSING state.

        These jobs likely failed but weren't marked as failed.
        Can be retried or marked as failed.

        Args:
            timeout_minutes: Consider job stale after this many minutes

        Returns:
            List of stale jobs
        """
        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        return (
            self.db.query(Job)
            .filter(
                Job.status == JobStatus.PROCESSING.value,
                Job.started_at < threshold,
            )
            .all()
        )

    def find_by_comfyui_prompt_id(self, prompt_id: str) -> Optional[Job]:
        """
        Find job by ComfyUI prompt ID.

        Used to update job status when ComfyUI webhook fires.

        Args:
            prompt_id: ComfyUI prompt ID

        Returns:
            Job or None
        """
        return (
            self.db.query(Job)
            .filter(Job.comfyui_prompt_id == prompt_id)
            .first()
        )

    def find_by_input_file_id(self, file_id: str) -> Optional[Job]:
        """
        Find job by input file ID.

        Prevents duplicate jobs for same file.

        Args:
            file_id: Google Drive file ID

        Returns:
            Job or None
        """
        return (
            self.db.query(Job)
            .filter(Job.input_file_id == file_id)
            .order_by(Job.created_at.desc())
            .first()
        )

    def count_user_jobs(
        self,
        user_id: str,
        status: JobStatus | None = None,
        since: datetime | None = None,
    ) -> int:
        """
        Count jobs for a user.

        Args:
            user_id: User UUID
            status: Optional status filter
            since: Only count jobs created after this date

        Returns:
            Number of jobs
        """
        query = self.db.query(func.count(Job.id)).filter(Job.user_id == user_id)

        if status:
            query = query.filter(Job.status == status.value)

        if since:
            query = query.filter(Job.created_at >= since)

        return query.scalar()

    def get_user_stats(
        self, user_id: str, since: datetime | None = None
    ) -> dict[str, int]:
        """
        Get job statistics for a user.

        Args:
            user_id: User UUID
            since: Only count jobs since this date

        Returns:
            Dictionary with job counts by status
        """
        query = self.db.query(Job.status, func.count(Job.id)).filter(
            Job.user_id == user_id
        )

        if since:
            query = query.filter(Job.created_at >= since)

        results = query.group_by(Job.status).all()

        return {status: count for status, count in results}

    def get_average_processing_time(
        self, preset_name: str | None = None
    ) -> float | None:
        """
        Get average job processing time.

        Args:
            preset_name: Optional preset filter

        Returns:
            Average processing time in seconds or None
        """
        query = self.db.query(
            func.avg(
                func.extract(
                    "epoch",
                    Job.completed_at - Job.started_at,
                )
            )
        ).filter(
            Job.status == JobStatus.COMPLETED.value,
            Job.started_at.isnot(None),
            Job.completed_at.isnot(None),
        )

        if preset_name:
            query = query.filter(Job.preset_name == preset_name)

        result = query.scalar()
        return float(result) if result else None

    def mark_job_queued(self, job_id: str) -> Optional[Job]:
        """
        Mark job as queued.

        Args:
            job_id: Job UUID

        Returns:
            Updated job or None
        """
        job = self.find_by_id(job_id)
        if not job:
            return None

        job.mark_queued()
        self.db.flush()
        self.db.refresh(job)
        return job

    def mark_job_processing(
        self, job_id: str, comfyui_prompt_id: str | None = None
    ) -> Optional[Job]:
        """
        Mark job as processing.

        Args:
            job_id: Job UUID
            comfyui_prompt_id: ComfyUI prompt ID

        Returns:
            Updated job or None
        """
        job = self.find_by_id(job_id)
        if not job:
            return None

        job.mark_processing(comfyui_prompt_id)
        self.db.flush()
        self.db.refresh(job)
        return job

    def mark_job_completed(
        self,
        job_id: str,
        output_file_id: str,
        output_file_name: str,
        output_file_url: str | None = None,
        execution_time: int | None = None,
    ) -> Optional[Job]:
        """
        Mark job as completed.

        Args:
            job_id: Job UUID
            output_file_id: Drive file ID of result
            output_file_name: Result file name
            output_file_url: Drive file URL
            execution_time: ComfyUI execution time in seconds

        Returns:
            Updated job or None
        """
        job = self.find_by_id(job_id)
        if not job:
            return None

        job.mark_completed(output_file_id, output_file_name, output_file_url)

        if execution_time:
            job.comfyui_execution_time = execution_time

        self.db.flush()
        self.db.refresh(job)
        return job

    def mark_job_failed(
        self,
        job_id: str,
        error_message: str,
        error_type: str | None = None,
    ) -> Optional[Job]:
        """
        Mark job as failed.

        Args:
            job_id: Job UUID
            error_message: Error description
            error_type: Error type/category

        Returns:
            Updated job or None
        """
        job = self.find_by_id(job_id)
        if not job:
            return None

        job.mark_failed(error_message, error_type)
        self.db.flush()
        self.db.refresh(job)
        return job

    def retry_job(self, job_id: str) -> Optional[Job]:
        """
        Retry a failed job.

        Args:
            job_id: Job UUID

        Returns:
            Updated job or None
        """
        job = self.find_by_id(job_id)
        if not job or not job.can_retry:
            return None

        job.increment_retry()
        job.mark_queued()

        self.db.flush()
        self.db.refresh(job)
        return job
