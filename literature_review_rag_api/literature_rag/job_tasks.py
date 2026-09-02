"""Queue-runnable job ingestion tasks.

process_job_upload is enqueued on the rq queue (module-level, importable by
the worker process) and also called inline by the synchronous upload route —
one code path for both. Task state lives in UploadTaskRecord (DB), so status
polling works regardless of which process ran the task.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _ingest_pdf_to_job(job_id: int, tmp_path: str, phase: str, topic: str,
                       original_filename: str) -> Dict[str, Any]:
    """Index a staged PDF into a job's knowledge base.

    Mirrors the historical synchronous route logic: index -> storage upload
    (with chunk rollback on storage failure) -> Document record -> job stats
    -> document relations. Opens its own DB session (worker-safe).
    Raises on failure; caller owns the UploadTaskRecord lifecycle.
    """
    # Imported at call time to avoid a routers<->tasks import cycle.
    from .config import load_config
    from .database import get_db_session, JobCRUD, DocumentCRUD, DocumentStatus
    from .routers.jobs import (build_job_indexer, compute_document_relations,
                               get_job_collection)
    from .storage import get_storage_auto

    config = load_config()
    temp_file = Path(tmp_path)
    tmp_name = temp_file.name  # "{upload_id}_{safe_filename}"
    upload_id, _, safe_filename = tmp_name.partition("_")

    db = get_db_session()
    try:
        job = JobCRUD.get_by_id(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        phases_config = config.data.phases if hasattr(config.data, "phases") else []
        phase_names = {p.get("name", ""): p.get("full_name", "") for p in phases_config}
        phase_name = phase_names.get(phase, phase)

        client, collection = get_job_collection(job)
        extractor_type = getattr(job, "extractor_type", "auto") or "auto"
        indexer = build_job_indexer(client, collection, job.id, extractor_type=extractor_type)

        result = indexer.index_pdf(
            pdf_path=temp_file,
            phase=phase,
            phase_name=phase_name,
            topic_category=topic,
        )
        if not result["success"]:
            raise RuntimeError(result.get("error", "Failed to index document"))

        storage = get_storage_auto()
        try:
            with open(temp_file, "rb") as fh:
                storage_key = storage.upload_pdf(
                    job_id=job_id, phase=phase, topic=topic,
                    filename=safe_filename, file_content=fh)
        except Exception as e:
            if result.get("doc_id"):
                existing = collection.get(where={"doc_id": result["doc_id"]}, include=[])
                if existing and existing.get("ids"):
                    collection.delete(ids=existing["ids"])
            raise RuntimeError(f"Storage upload failed: {e}")

        authors_value = None
        meta = result.get("metadata") or {}
        authors_value = meta.get("authors")
        if isinstance(authors_value, list):
            authors_value = ", ".join(authors_value)

        document = DocumentCRUD.create(
            db=db, job_id=job_id, doc_id=result["doc_id"],
            filename=tmp_name, original_filename=original_filename,
            title=meta.get("title"), authors=authors_value, year=meta.get("year"),
            phase=phase, topic_category=topic, doi=meta.get("doi"),
            file_size=temp_file.stat().st_size if temp_file.exists() else None,
            storage_key=storage_key, total_pages=meta.get("total_pages"),
        )
        DocumentCRUD.update_status(db, document,
                                   status=DocumentStatus.INDEXED.value,
                                   chunk_count=result["chunks_indexed"])
        job.document_count += 1
        job.chunk_count += result["chunks_indexed"]
        db.commit()

        try:
            compute_document_relations(db, job, collection, result["doc_id"])
        except Exception as e:
            logger.warning(f"Failed to compute document relations for {result['doc_id']}: {e}")

        logger.info(f"Indexed {result['chunks_indexed']} chunks for job {job_id} ({original_filename})")
        return {
            "success": True,
            "doc_id": result["doc_id"],
            "filename": original_filename,
            "chunks_indexed": result["chunks_indexed"],
            "metadata": result.get("metadata"),
        }
    finally:
        db.close()


def process_job_upload(task_id: str, job_id: int, tmp_path: str, phase: str,
                       topic: str, original_filename: str) -> Dict[str, Any]:
    """UploadTaskRecord lifecycle wrapper around _ingest_pdf_to_job.

    Never raises: failures are recorded on the task record and returned as
    {"success": False, "error": ...} so rq marks the job finished either way.
    Always removes the staged temp file.
    """
    from .database import get_db_session, UploadTaskCRUD

    db = get_db_session()
    rec = UploadTaskCRUD.get_by_task_id(db, task_id)
    try:
        if rec:
            UploadTaskCRUD.update(db, rec, status="processing", progress=10,
                                  started_at=datetime.utcnow())
        result = _ingest_pdf_to_job(job_id, tmp_path, phase, topic, original_filename)
        if rec:
            UploadTaskCRUD.update(db, rec, status="completed", progress=100,
                                  result_json=json.dumps(result, default=str),
                                  completed_at=datetime.utcnow())
        return result
    except Exception as e:
        logger.error(f"Job upload task {task_id} failed: {e}")
        if rec:
            try:
                UploadTaskCRUD.update(db, rec, status="failed", error=str(e),
                                      completed_at=datetime.utcnow())
            except Exception:
                pass
        return {"success": False, "error": str(e)}
    finally:
        db.close()
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
