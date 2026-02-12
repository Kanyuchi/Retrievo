"""Knowledge graph router."""

import json
import logging
import os
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import load_config
from ..database import (
    get_db, JobCRUD, KnowledgeClaimCRUD,
    KnowledgeEntityCRUD, KnowledgeEdgeCRUD
)
from ..models import KnowledgeGraphResponse, KnowledgeGraphRunResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["KnowledgeGraph"])

config = load_config()


def _extract_json(content: str) -> list:
    try:
        return json.loads(content)
    except Exception:
        pass
    if "```" in content:
        cleaned = content.split("```", 1)[-1]
        cleaned = cleaned.split("```", 1)[0].strip()
        try:
            return json.loads(cleaned)
        except Exception:
            return []
    return []


def _extract_entities_relations(claim_text: str) -> dict:
    graph_cfg = getattr(config, "graph", None)
    provider = getattr(graph_cfg, "llm_provider", "openai")
    model = getattr(graph_cfg, "llm_model", "gpt-4.1-mini")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OPENAI_API_KEY not configured for graph extraction"
            )
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    else:
        groq_api_key = config.llm.groq_api_key or os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Groq API key not configured for graph extraction"
            )
        from groq import Groq
        client = Groq(api_key=groq_api_key)

    prompt = (
        "Extract entities and relations from this claim. "
        "Return JSON with keys: entities (array of {name,type}) "
        "and relations (array of {source,target,relation}). "
        "Use short names, type in [concept, actor, institution, policy, place, theory].\n\n"
        f"Claim: {claim_text}\n\nJSON:"
    )

    response = client.chat.completions.create(
        model=model if provider == "openai" else config.llm.model,
        temperature=0.1,
        max_tokens=400,
        messages=[
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content.strip()
    data = _extract_json(content)
    if not isinstance(data, dict):
        return {"entities": [], "relations": []}
    return {
        "entities": data.get("entities", []) or [],
        "relations": data.get("relations", []) or []
    }


@router.post("/{job_id}/graph/build", response_model=KnowledgeGraphRunResponse)
async def build_knowledge_graph(
    job_id: int,
    claim_limit: int = Query(200, ge=1, le=1000),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = JobCRUD.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    claims = KnowledgeClaimCRUD.list_for_job(db, job_id, limit=claim_limit)
    KnowledgeEdgeCRUD.delete_for_job(db, job_id)
    KnowledgeEntityCRUD.delete_for_job(db, job_id)

    for claim in claims:
        extracted = _extract_entities_relations(claim.claim_text)
        entity_map = {}
        for ent in extracted.get("entities", [])[:10]:
            name = str(ent.get("name", "")).strip()
            if not name:
                continue
            entity_type = str(ent.get("type", "concept")).strip()
            entity = KnowledgeEntityCRUD.get_or_create(db, job_id, name, entity_type)
            entity_map[name] = entity

        for rel in extracted.get("relations", [])[:10]:
            source = str(rel.get("source", "")).strip()
            target = str(rel.get("target", "")).strip()
            relation_type = str(rel.get("relation", "related_to")).strip()
            if not source or not target:
                continue
            if source not in entity_map or target not in entity_map:
                continue
            KnowledgeEdgeCRUD.create(
                db=db,
                job_id=job_id,
                source_entity_id=entity_map[source].id,
                target_entity_id=entity_map[target].id,
                relation_type=relation_type,
                claim_id=claim.id,
                weight=1.0
            )
        # entities + edges are committed within CRUD helpers

    return {
        "claims_processed": len(claims),
        "entities_created": KnowledgeEntityCRUD.count_for_job(db, job_id),
        "edges_created": KnowledgeEdgeCRUD.count_for_job(db, job_id)
    }


@router.get("/{job_id}/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = JobCRUD.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    entities = KnowledgeEntityCRUD.list_for_job(db, job_id, limit=1000)
    edges = KnowledgeEdgeCRUD.list_for_job(db, job_id, limit=2000)

    return {
        "nodes": [
            {"id": e.id, "name": e.name, "entity_type": e.entity_type}
            for e in entities
        ],
        "edges": [
            {"source": e.source_entity_id, "target": e.target_entity_id, "relation_type": e.relation_type, "weight": e.weight}
            for e in edges
        ]
    }
