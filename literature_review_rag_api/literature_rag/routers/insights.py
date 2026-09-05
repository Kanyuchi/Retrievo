"""Knowledge insights (claims + gaps) router."""

import json
import logging
import os
from typing import Optional

import chromadb
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import load_config
from ..database import (
    get_db, JobCRUD,
    KnowledgeClaimCRUD, KnowledgeGapCRUD,
    KnowledgeEntityOccurrenceCRUD, KnowledgeEntityCRUD, KnowledgeClusterCRUD
)
from ..membership import require_job_role
from ..models import KnowledgeInsightsResponse, KnowledgeInsightsRunResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["KnowledgeInsights"])

config = load_config()


def _get_job_collection(job):
    from .jobs import get_job_collection
    _, collection = get_job_collection(job)
    return collection


def _get_job_collection_legacy_unused(job):
    client = chromadb.PersistentClient(path=config.storage.indices_path)
    return client.get_collection(job.collection_name)


def _extract_json(content: str) -> list:
    try:
        return json.loads(content)
    except Exception:
        pass

    # Fallback: extract JSON from fenced blocks
    if "```" in content:
        cleaned = content.split("```", 1)[-1]
        cleaned = cleaned.split("```", 1)[0]
        cleaned = cleaned.strip()
        # Fenced blocks often carry a language tag: ```json\n{...}
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except Exception:
            return []
    return []


def _build_doc_text(collection, doc_id: str, max_chars: int, max_paragraphs: int) -> list[tuple[int, str]]:
    results = collection.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
    docs = results.get("documents", []) or []
    metas = results.get("metadatas", []) or []
    pairs = list(zip(docs, metas))
    pairs.sort(key=lambda x: x[1].get("chunk_index", 0) if x[1] else 0)
    text = "\n\n".join(d for d, _ in pairs if d)
    text = text[:max_chars]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    paragraphs = paragraphs[:max_paragraphs]
    return list(enumerate(paragraphs, start=1))


def _extract_claims_from_paragraphs(paragraphs: list[tuple[int, str]]) -> list[dict]:
    if not paragraphs:
        return []

    insights_config = getattr(config, "insights", None)
    provider = getattr(insights_config, "llm_provider", "openai")
    model = getattr(insights_config, "llm_model", "gpt-4.1-mini")

    if provider == "openai":
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OPENAI_API_KEY not configured for claim extraction"
            )
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
    else:
        groq_api_key = config.llm.groq_api_key or os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Groq API key not configured for claim extraction"
            )
        from groq import Groq
        client = Groq(api_key=groq_api_key)

    numbered = "\n\n".join([f"[{idx}] {para}" for idx, para in paragraphs])

    prompt = (
        "You are extracting paragraph-level claims from a document.\n"
        "Return a JSON array of objects with keys: paragraph_index (int), claim (string).\n"
        "Use only the provided paragraphs. Keep each claim concise (1-2 sentences).\n"
        "If a paragraph has no clear claim, skip it.\n\n"
        f"Paragraphs:\n{numbered}\n\n"
        "JSON:"
    )

    response = client.chat.completions.create(
        model=model if provider == "openai" else config.llm.model,
        temperature=0.1,
        max_tokens=800,
        messages=[
            {"role": "system", "content": "Extract claims and return JSON only."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content.strip()
    data = _extract_json(content)
    if not isinstance(data, list):
        return []

    claims = []
    for item in data:
        if not isinstance(item, dict):
            continue
        paragraph_index = item.get("paragraph_index")
        claim_text = item.get("claim") or item.get("claim_text")
        if not claim_text:
            continue
        claims.append({
            "paragraph_index": paragraph_index,
            "claim_text": str(claim_text).strip()
        })
    return claims


@router.post("/{job_id}/insights/run", response_model=KnowledgeInsightsRunResponse)
async def run_knowledge_insights(
    job_id: int,
    doc_limit: int = Query(50, ge=1, le=500),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract paragraph-level claims and detect knowledge gaps for a job.
    """
    job = JobCRUD.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    require_job_role(db, job, current_user.id, "editor")

    from ..knowledge_tasks import run_insights_for_job
    return run_insights_for_job(job_id, doc_limit)


@router.post("/{job_id}/insights/run/async")
async def run_knowledge_insights_async(
    job_id: int,
    doc_limit: int = Query(50, ge=1, le=500),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enqueue a knowledge-insights build for background processing.

    Returns a task_id; poll GET /api/upload/{task_id}/status. Falls back to
    inline processing when the queue is unavailable.
    """
    import uuid as _uuid

    job = JobCRUD.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    require_job_role(db, job, current_user.id, "editor")

    from ..database import UploadTaskCRUD
    from ..knowledge_tasks import process_insights_build

    task_id = _uuid.uuid4().hex[:16]
    UploadTaskCRUD.create(db, task_id=task_id, filename="insights-build",
                          phase="-", topic="-", status="queued")

    try:
        from ..worker import WorkerManager
        WorkerManager(backend="auto").enqueue(
            process_insights_build, task_id, job.id, doc_limit, job_id=task_id)
    except Exception as e:
        logger.warning(f"Queue unavailable ({e}); processing insights build inline")
        process_insights_build(task_id, job.id, doc_limit)

    return {"task_id": task_id, "status_url": f"/api/upload/{task_id}/status"}


@router.get("/{job_id}/insights", response_model=KnowledgeInsightsResponse)
async def get_knowledge_insights(
    job_id: int,
    limit: int = Query(200, ge=1, le=1000),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get claims and detected gaps for a job.
    """
    job = JobCRUD.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    require_job_role(db, job, current_user.id, "viewer")

    claims = KnowledgeClaimCRUD.list_for_job(db, job_id, limit=limit)
    gaps = KnowledgeGapCRUD.list_for_job(db, job_id)
    gaps_by_claim = {}
    for gap in gaps:
        evidence = []
        if gap.evidence_json:
            try:
                evidence = json.loads(gap.evidence_json)
            except Exception:
                evidence = []
        gaps_by_claim.setdefault(gap.claim_id, []).append({
            "gap_type": gap.gap_type,
            "best_score": gap.best_score,
            "evidence_count": gap.evidence_count,
            "evidence": evidence
        })

    # Map doc_id -> cluster metadata
    cluster_name_by_id = {c.cluster_id: c.name for c in KnowledgeClusterCRUD.list_for_job(db, job_id)}

    doc_cluster_map: dict[str, tuple[Optional[str], Optional[str]]] = {}
    for claim in claims:
        if claim.doc_id in doc_cluster_map:
            continue
        entity_ids = KnowledgeEntityOccurrenceCRUD.list_entity_ids_for_doc(db, job_id, claim.doc_id)
        if not entity_ids:
            doc_cluster_map[claim.doc_id] = (None, None)
            continue
        entities = db.query(KnowledgeEntityCRUD.model).filter(
            KnowledgeEntityCRUD.model.job_id == job_id,
            KnowledgeEntityCRUD.model.id.in_(entity_ids)
        ).all()
        clusters = [e.cluster for e in entities if e.cluster]
        if not clusters:
            doc_cluster_map[claim.doc_id] = (None, None)
            continue
        cluster_id = max(set(clusters), key=clusters.count)
        doc_cluster_map[claim.doc_id] = (cluster_id, cluster_name_by_id.get(cluster_id))

    return {
        "total_claims": len(claims),
        "claims": [
            {
                "id": c.id,
                "doc_id": c.doc_id,
                "paragraph_index": c.paragraph_index,
                "claim_text": c.claim_text,
                "gaps": gaps_by_claim.get(c.id, []),
                "cluster_id": doc_cluster_map.get(c.doc_id, (None, None))[0],
                "cluster_name": doc_cluster_map.get(c.doc_id, (None, None))[1]
            }
            for c in claims
        ]
    }
