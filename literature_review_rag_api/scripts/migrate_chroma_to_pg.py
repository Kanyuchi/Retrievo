"""Migrate all job Chroma collections into Postgres vector_chunks.

Idempotent: PgVectorStore.add upserts on (collection, chunk_id).
Usage: python scripts/migrate_chroma_to_pg.py [--indices-path ./indices] [--dry-run]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb  # noqa: E402
from literature_rag.database import engine, get_db_session, Job  # noqa: E402
from literature_rag.pg_store import PgVectorStore, ensure_schema  # noqa: E402

BATCH = 200


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices-path", default="./indices")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.dry_run:
        ensure_schema(engine)
    client = chromadb.PersistentClient(path=args.indices_path)

    db = get_db_session()
    try:
        jobs = db.query(Job).all()
    finally:
        db.close()

    total = 0
    mismatches = 0
    for job in jobs:
        try:
            col = client.get_collection(job.collection_name)
        except Exception:
            print(f"job {job.id} ({job.collection_name}): no chroma collection, skipping")
            continue
        n = col.count()
        print(f"job {job.id} ({job.collection_name}): {n} chunks")
        if args.dry_run or n == 0:
            continue
        store = PgVectorStore(job.collection_name, engine)
        offset = 0
        while offset < n:
            batch = col.get(include=["documents", "metadatas", "embeddings"],
                            limit=BATCH, offset=offset)
            if not batch["ids"]:
                break
            store.add(ids=batch["ids"],
                      embeddings=[list(e) for e in batch["embeddings"]],
                      documents=batch["documents"],
                      metadatas=batch["metadatas"])
            offset += len(batch["ids"])
            total += len(batch["ids"])
        migrated = store.count()
        status = "OK" if migrated >= n else "MISMATCH"
        if status == "MISMATCH":
            mismatches += 1
        print(f"  -> pg rows: {migrated}/{n} {status}")
    print(f"total chunks migrated: {total}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
