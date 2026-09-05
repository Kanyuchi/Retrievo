"""Queue-runnable knowledge-insights and knowledge-graph build tasks.

run_insights_for_job / run_graph_build_for_job hold the actual work (moved
out of routers/insights.py and routers/graph.py verbatim) and open their own
DB session, so they're safe to call from a worker process. process_insights_build
and process_graph_build are UploadTaskRecord lifecycle wrappers, mirroring
job_tasks.process_job_upload: they are enqueued on the rq queue (module-level,
importable by the worker process) and also called inline by the synchronous
and async routes as a fallback when the queue is unavailable.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def run_insights_for_job(job_id: int, doc_limit: int) -> Dict[str, Any]:
    """Extract paragraph-level claims and detect knowledge gaps for a job.

    Mirrors the historical run_knowledge_insights route logic: config reading,
    clearing existing claims/gaps, per-document claim extraction + evidence
    based gap detection. Opens its own DB session (worker-safe).
    """
    # Imported at call time to avoid a routers<->tasks import cycle.
    from .config import load_config
    from .database import (
        get_db_session, JobCRUD, DocumentCRUD,
        KnowledgeClaimCRUD, KnowledgeGapCRUD
    )
    from .embeddings import get_embeddings
    from .routers.insights import (
        _get_job_collection, _build_doc_text, _extract_claims_from_paragraphs
    )

    config = load_config()
    db = get_db_session()
    try:
        job = JobCRUD.get_by_id(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

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
                        include=["distances", "documents", "metadatas"]
                    )
                    distances = result.get("distances", [[]])[0] or []
                    documents = result.get("documents", [[]])[0] or []
                    metadatas = result.get("metadatas", [[]])[0] or []
                    if distances:
                        best_score = max(0.0, 1.0 - float(distances[0]))
                        evidence_count = sum(1 for d in distances if (1.0 - float(d)) >= weak_threshold)
                    else:
                        best_score = 0.0
                        evidence_count = 0
                except Exception:
                    best_score = 0.0
                    evidence_count = 0
                    documents = []
                    metadatas = []

                evidence_snippets = []
                for doc_text, meta, dist in zip(documents[:2], metadatas[:2], distances[:2]):
                    score = max(0.0, 1.0 - float(dist)) if dist is not None else 0.0
                    evidence_snippets.append({
                        "doc_id": meta.get("doc_id") if meta else None,
                        "title": meta.get("title") if meta else None,
                        "score": score,
                        "snippet": (doc_text or "")[:300]
                    })

                if best_score < missing_threshold:
                    KnowledgeGapCRUD.create(
                        db=db,
                        job_id=job_id,
                        claim_id=claim_record.id,
                        gap_type="missing_evidence",
                        best_score=best_score,
                        evidence_count=evidence_count,
                        evidence_json=json.dumps(evidence_snippets)
                    )
                    gaps_detected += 1
                elif evidence_count < min_evidence:
                    KnowledgeGapCRUD.create(
                        db=db,
                        job_id=job_id,
                        claim_id=claim_record.id,
                        gap_type="weak_coverage",
                        best_score=best_score,
                        evidence_count=evidence_count,
                        evidence_json=json.dumps(evidence_snippets)
                    )
                    gaps_detected += 1

        return {
            "documents_processed": len(documents),
            "claims_extracted": claims_extracted,
            "gaps_detected": gaps_detected
        }
    finally:
        db.close()


def run_graph_build_for_job(job_id: int, claim_limit: int) -> Dict[str, Any]:
    """Build the knowledge graph (entities + relations + clusters) for a job.

    Mirrors the historical build_knowledge_graph route logic: FK-safe
    clearing, per-claim entity/relation extraction, graph refinement,
    persistence, and cluster summaries. Opens its own DB session
    (worker-safe).
    """
    # Imported at call time to avoid a routers<->tasks import cycle.
    from .config import load_config
    from .database import (
        get_db_session, KnowledgeClaimCRUD,
        KnowledgeEntityCRUD, KnowledgeEdgeCRUD,
        KnowledgeEntityOccurrenceCRUD, KnowledgeClusterCRUD
    )
    from .routers.graph import _extract_entities_relations, _refine_graph, _summarize_cluster

    config = load_config()
    db = get_db_session()
    try:
        claims = KnowledgeClaimCRUD.list_for_job(db, job_id, limit=claim_limit)
        # FK-safe order: occurrences and edges reference entities, so they must
        # be deleted first (Postgres enforces this; SQLite silently didn't).
        KnowledgeEntityOccurrenceCRUD.delete_for_job(db, job_id)
        KnowledgeEdgeCRUD.delete_for_job(db, job_id)
        KnowledgeEntityCRUD.delete_for_job(db, job_id)
        KnowledgeClusterCRUD.delete_for_job(db, job_id)

        raw_entities: List[Dict[str, Any]] = []
        raw_relations: List[Dict[str, Any]] = []

        for claim in claims:
            extracted = _extract_entities_relations(claim.claim_text)
            for ent in extracted.get("entities", [])[:10]:
                name = str(ent.get("name", "")).strip()
                if not name:
                    continue
                entity_type = str(ent.get("type", "concept")).strip()
                raw_entities.append({
                    "name": name,
                    "type": entity_type,
                    "doc_id": claim.doc_id,
                    "claim_id": claim.id,
                    "paragraph_index": claim.paragraph_index
                })

            for rel in extracted.get("relations", [])[:10]:
                source = str(rel.get("source", "")).strip()
                target = str(rel.get("target", "")).strip()
                relation_type = str(rel.get("relation", "related_to")).strip()
                if not source or not target:
                    continue
                raw_relations.append({"source": source, "target": target, "relation": relation_type})

        refined = _refine_graph(raw_entities, raw_relations)
        entity_map: Dict[str, Any] = {}

        for ent in refined.get("entities", [])[:400]:
            name = str(ent.get("name", "")).strip()
            if not name:
                continue
            entity_type = str(ent.get("type", "concept")).strip()
            cluster = str(ent.get("cluster", "")).strip() or None
            entity = KnowledgeEntityCRUD.get_or_create(db, job_id, name, entity_type, cluster)
            entity_map[name] = entity

        for ent in raw_entities:
            name = str(ent.get("name", "")).strip()
            if not name or name not in entity_map:
                continue
            KnowledgeEntityOccurrenceCRUD.create(
                db=db,
                job_id=job_id,
                entity_id=entity_map[name].id,
                doc_id=str(ent.get("doc_id", "")),
                claim_id=ent.get("claim_id"),
                paragraph_index=ent.get("paragraph_index")
            )

        for rel in refined.get("relations", [])[:800]:
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
                weight=1.0
            )

        graph_cfg = getattr(config, "graph", None)
        if getattr(graph_cfg, "cluster_summaries_enabled", True):
            # Build cluster summaries (connected components)
            entities = KnowledgeEntityCRUD.list_for_job(db, job_id, limit=1000)
            edges = KnowledgeEdgeCRUD.list_for_job(db, job_id, limit=2000)
            adjacency = {e.id: set() for e in entities}
            for edge in edges:
                adjacency.setdefault(edge.source_entity_id, set()).add(edge.target_entity_id)
                adjacency.setdefault(edge.target_entity_id, set()).add(edge.source_entity_id)

            visited = set()
            clusters = []
            for entity in entities:
                if entity.id in visited:
                    continue
                stack = [entity.id]
                component = []
                while stack:
                    node_id = stack.pop()
                    if node_id in visited:
                        continue
                    visited.add(node_id)
                    component.append(node_id)
                    for neighbor in adjacency.get(node_id, []):
                        if neighbor not in visited:
                            stack.append(neighbor)
                if component:
                    clusters.append(component)

            for idx, component in enumerate(clusters, start=1):
                cluster_id = f"cluster_{idx}"
                cluster_entities = [e for e in entities if e.id in component]
                entity_names = [e.name for e in cluster_entities]
                relation_names = [
                    edge.relation_type
                    for edge in edges
                    if edge.source_entity_id in component or edge.target_entity_id in component
                ]
                summary = _summarize_cluster(entity_names, relation_names)
                KnowledgeClusterCRUD.upsert(
                    db=db,
                    job_id=job_id,
                    cluster_id=cluster_id,
                    name=entity_names[0] if entity_names else cluster_id,
                    summary=summary,
                    node_count=len(component)
                )
                for e in cluster_entities:
                    if not e.cluster:
                        e.cluster = cluster_id
                db.commit()

        return {
            "claims_processed": len(claims),
            "entities_created": KnowledgeEntityCRUD.count_for_job(db, job_id),
            "edges_created": KnowledgeEdgeCRUD.count_for_job(db, job_id)
        }
    finally:
        db.close()


def process_insights_build(task_id: str, job_id: int, doc_limit: int) -> Dict[str, Any]:
    """UploadTaskRecord lifecycle wrapper around run_insights_for_job.

    Never raises: failures are recorded on the task record and returned as
    {"success": False, "error": ...} so rq marks the job finished either way.
    """
    from .database import get_db_session, UploadTaskCRUD

    db = get_db_session()
    rec = UploadTaskCRUD.get_by_task_id(db, task_id)
    try:
        if rec:
            UploadTaskCRUD.update(db, rec, status="processing", progress=10,
                                  started_at=datetime.utcnow())
        result = run_insights_for_job(job_id, doc_limit)
        if rec:
            UploadTaskCRUD.update(db, rec, status="completed", progress=100,
                                  result_json=json.dumps(result, default=str),
                                  completed_at=datetime.utcnow())
        return result
    except Exception as e:
        logger.error(f"Insights build task {task_id} failed: {e}")
        if rec:
            try:
                UploadTaskCRUD.update(db, rec, status="failed", error=str(e),
                                      completed_at=datetime.utcnow())
            except Exception:
                pass
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def process_graph_build(task_id: str, job_id: int, claim_limit: int) -> Dict[str, Any]:
    """UploadTaskRecord lifecycle wrapper around run_graph_build_for_job.

    Never raises: failures are recorded on the task record and returned as
    {"success": False, "error": ...} so rq marks the job finished either way.
    """
    from .database import get_db_session, UploadTaskCRUD

    db = get_db_session()
    rec = UploadTaskCRUD.get_by_task_id(db, task_id)
    try:
        if rec:
            UploadTaskCRUD.update(db, rec, status="processing", progress=10,
                                  started_at=datetime.utcnow())
        result = run_graph_build_for_job(job_id, claim_limit)
        if rec:
            UploadTaskCRUD.update(db, rec, status="completed", progress=100,
                                  result_json=json.dumps(result, default=str),
                                  completed_at=datetime.utcnow())
        return result
    except Exception as e:
        logger.error(f"Graph build task {task_id} failed: {e}")
        if rec:
            try:
                UploadTaskCRUD.update(db, rec, status="failed", error=str(e),
                                      completed_at=datetime.utcnow())
            except Exception:
                pass
        return {"success": False, "error": str(e)}
    finally:
        db.close()
