"""Background Task Management for Literature RAG

Provides task tracking and async processing for PDF uploads.
Uses in-memory storage (can be upgraded to Redis for production).
"""

import logging
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
import shutil

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UploadTask:
    """Represents an upload task."""
    task_id: str
    filename: str
    phase: str
    topic: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0  # 0-100
    message: str = "Waiting to start..."
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # File paths
    temp_file_path: Optional[str] = None
    storage_file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "task_id": self.task_id,
            "filename": self.filename,
            "phase": self.phase,
            "topic": self.topic,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error
        }


class TaskStore:
    """
    In-memory task store for tracking upload jobs.

    Thread-safe implementation for use with FastAPI BackgroundTasks.
    For production with multiple workers, replace with Redis.
    """

    def __init__(self, max_tasks: int = 100):
        """
        Initialize task store.

        Args:
            max_tasks: Maximum tasks to keep in memory (oldest are evicted)
        """
        self._tasks: Dict[str, UploadTask] = {}
        self._lock = Lock()
        self._max_tasks = max_tasks

    def create_task(
        self,
        filename: str,
        phase: str,
        topic: str,
        temp_file_path: Optional[str] = None
    ) -> UploadTask:
        """
        Create a new upload task.

        Args:
            filename: Original filename
            phase: Target phase
            topic: Target topic
            temp_file_path: Path to temporary file

        Returns:
            Created UploadTask
        """
        task_id = str(uuid.uuid4())[:12]

        task = UploadTask(
            task_id=task_id,
            filename=filename,
            phase=phase,
            topic=topic,
            temp_file_path=temp_file_path
        )

        with self._lock:
            # Evict old tasks if needed
            if len(self._tasks) >= self._max_tasks:
                self._evict_oldest()

            self._tasks[task_id] = task

        logger.info(f"Created upload task {task_id} for {filename}")
        return task

    def get_task(self, task_id: str) -> Optional[UploadTask]:
        """Get task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[UploadTask]:
        """
        Update task status and progress.

        Args:
            task_id: Task identifier
            status: New status
            progress: Progress percentage (0-100)
            message: Status message
            result: Result data (on completion)
            error: Error message (on failure)

        Returns:
            Updated task or None if not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if status:
                task.status = status
                if status == TaskStatus.PROCESSING and not task.started_at:
                    task.started_at = datetime.now()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    task.completed_at = datetime.now()

            if progress is not None:
                task.progress = min(100, max(0, progress))

            if message:
                task.message = message

            if result:
                task.result = result

            if error:
                task.error = error

            return task

    def list_tasks(self, limit: int = 20) -> list[UploadTask]:
        """List recent tasks."""
        with self._lock:
            tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.created_at,
                reverse=True
            )
            return tasks[:limit]

    def _evict_oldest(self):
        """Remove oldest completed/failed tasks."""
        # First try to remove completed/failed tasks
        completed = [
            (k, v) for k, v in self._tasks.items()
            if v.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]

        if completed:
            # Sort by completion time, remove oldest
            completed.sort(key=lambda x: x[1].completed_at or x[1].created_at)
            oldest_id = completed[0][0]
            del self._tasks[oldest_id]
            logger.debug(f"Evicted completed task {oldest_id}")
        else:
            # No completed tasks, remove oldest pending
            pending = sorted(
                self._tasks.items(),
                key=lambda x: x[1].created_at
            )
            if pending:
                oldest_id = pending[0][0]
                del self._tasks[oldest_id]
                logger.debug(f"Evicted oldest task {oldest_id}")


# Global task store instance
task_store = TaskStore()


async def process_pdf_task(
    task_id: str,
    indexer,
    temp_file_path: Path,
    phase: str,
    phase_name: str,
    topic: str,
    storage_path: Path,
    filename: str
):
    """
    Background task to process and index a PDF.

    Args:
        task_id: Task identifier
        indexer: DocumentIndexer instance
        temp_file_path: Path to temporary uploaded file
        phase: Phase identifier
        phase_name: Phase display name
        topic: Topic category
        storage_path: Path to permanent storage
        filename: Original filename
    """
    try:
        # Update status to processing
        task_store.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=10,
            message="Starting PDF extraction..."
        )

        # Small delay to allow status to be read
        await asyncio.sleep(0.1)

        # Update progress - extracting
        task_store.update_task(
            task_id,
            progress=20,
            message="Extracting text and metadata..."
        )

        # Index the PDF (this is the heavy operation)
        result = indexer.index_pdf(
            pdf_path=temp_file_path,
            phase=phase,
            phase_name=phase_name,
            topic_category=topic
        )

        # Update progress - embedding
        task_store.update_task(
            task_id,
            progress=70,
            message="Generating embeddings..."
        )

        await asyncio.sleep(0.1)

        if result["success"]:
            # Move to permanent storage
            task_store.update_task(
                task_id,
                progress=90,
                message="Moving to permanent storage..."
            )

            phase_topic_dir = storage_path / phase / topic
            phase_topic_dir.mkdir(parents=True, exist_ok=True)

            permanent_file = phase_topic_dir / filename
            shutil.move(str(temp_file_path), str(permanent_file))

            # Mark as completed
            task_store.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                progress=100,
                message=f"Successfully indexed {result['chunks_indexed']} chunks",
                result={
                    "doc_id": result["doc_id"],
                    "filename": filename,
                    "chunks_indexed": result["chunks_indexed"],
                    "metadata": result["metadata"]
                }
            )

            logger.info(f"Task {task_id} completed: {result['chunks_indexed']} chunks indexed")
        else:
            # Mark as failed
            task_store.update_task(
                task_id,
                status=TaskStatus.FAILED,
                progress=0,
                message="Indexing failed",
                error=result.get("error", "Unknown error during indexing")
            )

            # Cleanup temp file
            if temp_file_path.exists():
                temp_file_path.unlink()

            logger.error(f"Task {task_id} failed: {result.get('error')}")

    except Exception as e:
        logger.exception(f"Task {task_id} failed with exception")

        task_store.update_task(
            task_id,
            status=TaskStatus.FAILED,
            progress=0,
            message="Processing failed",
            error=str(e)
        )

        # Cleanup temp file
        try:
            if temp_file_path.exists():
                temp_file_path.unlink()
        except Exception:
            pass


def run_async_task(coro):
    """
    Run an async coroutine in a sync context.
    Used for BackgroundTasks which expects sync functions.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
