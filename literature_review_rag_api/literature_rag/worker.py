"""Worker Queue Module for Literature RAG

Provides background job processing for heavy tasks like PDF indexing.
Supports both Redis-backed (rq) and in-memory (fallback) backends.
"""

import logging
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from threading import Thread
from queue import Queue as ThreadQueue
import json

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass
class JobResult:
    """Result of a background job."""
    job_id: str
    status: JobStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class WorkerBackend(ABC):
    """Abstract base class for worker backends."""

    @abstractmethod
    def enqueue(
        self,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Enqueue a job for processing.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            job_id: Optional job ID (generated if not provided)
            **kwargs: Keyword arguments for the function

        Returns:
            Job ID
        """
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[JobResult]:
        """Get job status and result.

        Args:
            job_id: Job ID to look up

        Returns:
            JobResult or None if not found
        """
        pass

    @abstractmethod
    def get_queue_length(self) -> int:
        """Get number of jobs in queue."""
        pass


class InMemoryWorker(WorkerBackend):
    """In-memory worker backend using threads.

    Suitable for single-instance deployments without Redis.
    Jobs run in background threads.
    """

    def __init__(self, num_workers: int = 2):
        """Initialize in-memory worker.

        Args:
            num_workers: Number of worker threads
        """
        self._jobs: Dict[str, JobResult] = {}
        self._queue: ThreadQueue = ThreadQueue()
        self._workers: List[Thread] = []
        self._running = True

        # Start worker threads
        for i in range(num_workers):
            t = Thread(target=self._worker_loop, daemon=True, name=f"worker-{i}")
            t.start()
            self._workers.append(t)

        logger.info(f"In-memory worker started with {num_workers} threads")

    def _worker_loop(self):
        """Worker thread loop."""
        while self._running:
            try:
                item = self._queue.get(timeout=1.0)
                if item is None:
                    continue

                job_id, func, args, kwargs = item

                # Update status to started
                if job_id in self._jobs:
                    self._jobs[job_id].status = JobStatus.STARTED
                    self._jobs[job_id].started_at = datetime.utcnow()

                try:
                    # Execute the function
                    result = func(*args, **kwargs)

                    # Update with result
                    if job_id in self._jobs:
                        self._jobs[job_id].status = JobStatus.FINISHED
                        self._jobs[job_id].result = result
                        self._jobs[job_id].finished_at = datetime.utcnow()

                except Exception as e:
                    logger.error(f"Job {job_id} failed: {e}")
                    if job_id in self._jobs:
                        self._jobs[job_id].status = JobStatus.FAILED
                        self._jobs[job_id].error = str(e)
                        self._jobs[job_id].finished_at = datetime.utcnow()

            except Exception:
                # Queue.get timeout
                pass

    def enqueue(
        self,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Enqueue a job for processing."""
        job_id = job_id or str(uuid.uuid4())

        # Create job record
        self._jobs[job_id] = JobResult(
            job_id=job_id,
            status=JobStatus.QUEUED,
            meta={"queued_at": datetime.utcnow().isoformat()}
        )

        # Add to queue
        self._queue.put((job_id, func, args, kwargs))
        logger.info(f"Job {job_id} enqueued (in-memory)")

        return job_id

    def get_job(self, job_id: str) -> Optional[JobResult]:
        """Get job status and result."""
        return self._jobs.get(job_id)

    def get_queue_length(self) -> int:
        """Get number of jobs in queue."""
        return self._queue.qsize()

    def shutdown(self):
        """Shutdown worker threads."""
        self._running = False
        for _ in self._workers:
            self._queue.put(None)
        for t in self._workers:
            t.join(timeout=2.0)


class RedisWorker(WorkerBackend):
    """Redis-backed worker using rq (Redis Queue).

    Suitable for distributed deployments with multiple workers.
    Requires Redis server and rq package.
    """

    def __init__(
        self,
        redis_url: str = None,
        queue_name: str = "literature_rag"
    ):
        """Initialize Redis worker.

        Args:
            redis_url: Redis connection URL
            queue_name: Name of the job queue
        """
        try:
            from redis import Redis
            from rq import Queue
        except ImportError:
            raise ImportError("redis and rq packages required. Run: pip install redis rq")

        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")

        self._redis = Redis.from_url(redis_url)
        self._queue = Queue(queue_name, connection=self._redis)
        self._queue_name = queue_name

        logger.info(f"Redis worker connected to {redis_url}, queue: {queue_name}")

    def enqueue(
        self,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Enqueue a job for processing."""
        job_id = job_id or str(uuid.uuid4())

        job = self._queue.enqueue(
            func,
            *args,
            job_id=job_id,
            **kwargs
        )

        logger.info(f"Job {job.id} enqueued (Redis)")
        return job.id

    def get_job(self, job_id: str) -> Optional[JobResult]:
        """Get job status and result."""
        try:
            from rq.job import Job
        except ImportError:
            return None

        try:
            job = Job.fetch(job_id, connection=self._redis)

            status_map = {
                "queued": JobStatus.QUEUED,
                "started": JobStatus.STARTED,
                "finished": JobStatus.FINISHED,
                "failed": JobStatus.FAILED
            }

            return JobResult(
                job_id=job.id,
                status=status_map.get(job.get_status(), JobStatus.QUEUED),
                result=job.result,
                error=job.exc_info if job.is_failed else None,
                started_at=job.started_at,
                finished_at=job.ended_at,
                meta=job.meta or {}
            )
        except Exception as e:
            logger.error(f"Failed to fetch job {job_id}: {e}")
            return None

    def get_queue_length(self) -> int:
        """Get number of jobs in queue."""
        return len(self._queue)


class WorkerManager:
    """Manager for worker backend selection and operations."""

    _instance: Optional["WorkerManager"] = None

    def __new__(cls, backend: str = "auto", **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, backend: str = "auto", **kwargs):
        """Initialize worker manager.

        Args:
            backend: "redis", "memory", or "auto" (tries Redis, falls back to memory)
            **kwargs: Backend-specific configuration
        """
        if self._initialized:
            return

        self._backend: Optional[WorkerBackend] = None
        self._backend_name = "none"

        if backend == "auto":
            # Try Redis first, fall back to memory
            try:
                redis_url = kwargs.get("redis_url") or os.getenv("REDIS_URL")
                if redis_url:
                    self._backend = RedisWorker(redis_url=redis_url, **kwargs)
                    self._backend_name = "redis"
                else:
                    raise ValueError("No Redis URL configured")
            except Exception as e:
                logger.warning(f"Redis worker not available: {e}. Using in-memory worker.")
                self._backend = InMemoryWorker(**kwargs)
                self._backend_name = "memory"

        elif backend == "redis":
            self._backend = RedisWorker(**kwargs)
            self._backend_name = "redis"

        elif backend == "memory":
            self._backend = InMemoryWorker(**kwargs)
            self._backend_name = "memory"

        else:
            raise ValueError(f"Unknown backend: {backend}")

        self._initialized = True
        logger.info(f"Worker manager initialized with {self._backend_name} backend")

    def enqueue(
        self,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Enqueue a job."""
        if self._backend is None:
            raise RuntimeError("Worker not initialized")
        return self._backend.enqueue(func, *args, job_id=job_id, **kwargs)

    def get_job(self, job_id: str) -> Optional[JobResult]:
        """Get job status."""
        if self._backend is None:
            return None
        return self._backend.get_job(job_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            "backend": self._backend_name,
            "queue_length": self._backend.get_queue_length() if self._backend else 0
        }

    @property
    def backend_name(self) -> str:
        """Get backend name."""
        return self._backend_name


# Global worker instance
_worker: Optional[WorkerManager] = None


def get_worker(backend: str = "auto", **kwargs) -> WorkerManager:
    """Get global worker instance.

    Args:
        backend: "redis", "memory", or "auto"
        **kwargs: Backend configuration

    Returns:
        WorkerManager singleton
    """
    global _worker
    if _worker is None:
        _worker = WorkerManager(backend=backend, **kwargs)
    return _worker


def enqueue_job(func: Callable, *args, job_id: Optional[str] = None, **kwargs) -> str:
    """Convenience function to enqueue a job."""
    return get_worker().enqueue(func, *args, job_id=job_id, **kwargs)


def get_job_status(job_id: str) -> Optional[JobResult]:
    """Convenience function to get job status."""
    return get_worker().get_job(job_id)
