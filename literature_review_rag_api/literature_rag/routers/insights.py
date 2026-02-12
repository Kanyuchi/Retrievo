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
    get_db, JobCRUD, DocumentCRUD,
    KnowledgeClaimCRUD, KnowledgeGapCRUD
)
from ..embeddings import get_embeddings
from ..models import KnowledgeInsightsResponse, KnowledgeInsightsRunResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["KnowledgeInsights"])

config = load_config()


def _get_job_collection(job):
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
    if job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    documents = DocumentCRUD.get_job_documents(db, job_id)[:doc_limit]
    collection = _get_job_collection(job)
    embeddings = get_embeddings(config.embedding)

    insights_config = getattr(config, "insights", None)
    max_chars = getattr(insights_config, "max_doc_chars", 12000)
    max_paragraphs = getattr(insights_config, "max_paragraphs", 12)
    max_claims_per_doc = getattr(insights_config, "max_claims_per_doc", 8)
    missing_threshold = getattr(insights_config, "missing_threshold", 0.25)
    weak_threshold = getattr(insights_config, "weak_threshold", 0.35)
    min_evidence = getattr(insights_config, "min_evidence", 2)

    # Clear existing
    KnowledgeGapCRUD.delete_for_job(db, job_id)
    KnowledgeClaimCRUD.delete_for_job(db, job_id)

    claims_extracted = 0
    gaps_detected = 0

    for doc in documents:
        paragraphs = _build_doc_text(collection, doc.doc_id, max_chars, max_paragraphs)
        if not paragraphs:
            continue

        claims = _extract_claims_from_paragraphs(paragraphs)
        if not claims:
            continue

        for claim in claims[:max_claims_per_doc]:
            claim_record = KnowledgeClaimCRUD.create(
                db=db,
                job_id=job_id,
                doc_id=doc.doc_id,
                claim_text=claim["claim_text"],
                paragraph_index=claim.get("paragraph_index")
            )
            claims_extracted += 1

            # Evidence check via vector search
            try:
                query_vec = embeddings.embed_query(claim["claim_text"])
                result = collection.query(
                    query_embeddings=[query_vec],
                    n_results=5,
                    include=["distances"]
                )
                distances = result.get("distances", [[]])[0] or []
                if distances:
                    best_score = max(0.0, 1.0 - float(distances[0]))
                    evidence_count = sum(1 for d in distances if (1.0 - float(d)) >= weak_threshold)
                else:
                    best_score = 0.0
                    evidence_count = 0
            except Exception:
                best_score = 0.0
                evidence_count = 0

            if best_score < missing_threshold:
                KnowledgeGapCRUD.create(
                    db=db,
                    job_id=job_id,
                    claim_id=claim_record.id,
                    gap_type="missing_evidence",
                    best_score=best_score,
                    evidence_count=evidence_count
                )
                gaps_detected += 1
            elif evidence_count < min_evidence:
                KnowledgeGapCRUD.create(
                    db=db,
                    job_id=job_id,
                    claim_id=claim_record.id,
                    gap_type="weak_coverage",
                    best_score=best_score,
                    evidence_count=evidence_count
                )
                gaps_detected += 1

    return {
        "documents_processed": len(documents),
        "claims_extracted": claims_extracted,
        "gaps_detected": gaps_detected
    }


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
    if job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    claims = KnowledgeClaimCRUD.list_for_job(db, job_id, limit=limit)
    gaps = KnowledgeGapCRUD.list_for_job(db, job_id)
    gaps_by_claim = {}
    for gap in gaps:
        gaps_by_claim.setdefault(gap.claim_id, []).append({
            "gap_type": gap.gap_type,
            "best_score": gap.best_score,
            "evidence_count": gap.evidence_count
        })

    return {
        "total_claims": len(claims),
        "claims": [
            {
                "id": c.id,
                "doc_id": c.doc_id,
                "paragraph_index": c.paragraph_index,
                "claim_text": c.claim_text,
                "gaps": gaps_by_claim.get(c.id, [])
            }
            for c in claims
        ]
    }
