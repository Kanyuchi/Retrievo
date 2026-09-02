# Phase 2b: Ingestion Queue, Redis State, Multi-Worker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Per-job uploads run on a crash-safe Redis (rq) queue instead of blocking request threads; rate limiting and OAuth state become Redis-backed; the API serves with 2 uvicorn workers.

**Architecture:** A `worker` compose service (same image) runs `rq worker`; the API enqueues `literature_rag.job_tasks.process_job_upload` and returns a `task_id`; status polling reuses the existing DB-backed `UploadTaskRecord` (works across processes). Files are staged under the shared `/app/uploads` volume. The frontend's job-upload method switches to async+poll internally, preserving its promise contract so `JobDetail.tsx`/`Files.tsx` are untouched. Rate limiting gains a Redis fixed-window counter selected when `REDIS_URL` is set; OAuth state is already Redis-aware (auth.py:124) — providing Redis activates it with zero code.

**Tech Stack:** rq ≥1.16, redis ≥5 (already a dep), redis:7-alpine service, uvicorn `--workers 2`.

**Spec:** `ROADMAP.md` Phase 2 items 3–4. Verified facts: `worker.py` has `RedisWorker` (rq-based, enqueue/get_job) + `WorkerManager(backend="auto")` that picks Redis when `REDIS_URL` set; **rq is not in requirements**; sync upload route `routers/jobs.py upload_to_job` (~line 1295); global async pattern: `POST /api/upload/async` + `GET /api/upload/{task_id}/status` reading `UploadTaskRecord` via `UploadTaskCRUD` (`api.py:1593-1731`, `tasks.py`); frontend job upload at `webapp/src/lib/api.ts:1053`; rate limiter `SlidingWindowCounter` in-memory (`rate_limiter.py:42`); compose services: api/nginx/certbot only; Dockerfile CMD single-worker uvicorn.

## Global Constraints
- Suite green after every task: `TEST_PG_URL=postgresql://postgres:test@localhost:55433/postgres ./venv/bin/python -m pytest -q tests`
- Old sync route `POST /api/jobs/{id}/upload` stays (API compat); frontend moves to async.
- rq task functions must be module-level importable (rq pickles dotted paths).
- Worker staging dir = `/app/uploads/tmp` (shared api↔worker volume). Never `/tmp` (not shared).
- Commit per task, `type: description`.

---

### Task 1: rq dependency + compose services (redis, worker) + multi-worker CMD

**Files:** Modify `requirements.txt`, `requirements-prod.txt` (add `rq>=1.16` after `redis>=5.0.0`), `docker-compose.yml`, `Dockerfile`.

- [ ] **Step 1:** Add `rq>=1.16` to both requirements files; `./venv/bin/pip install -q rq` locally.
- [ ] **Step 2:** In `docker-compose.yml` add under `services:` (same level as `api:`):

```yaml
  redis:
    image: redis:7-alpine
    container_name: lit-rag-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: lit-rag-worker
    command: rq worker --url redis://redis:6379/0 literature_rag
    env_file: .env
    environment:
      - DATABASE_URL=${DATABASE_URL:-sqlite:///./data/db/literature_rag.db}
      - VECTOR_BACKEND=${VECTOR_BACKEND:-chroma}
      - REDIS_URL=redis://redis:6379/0
      - AWS_S3_BUCKET=${AWS_S3_BUCKET:-lit-rag-flow}
      - AWS_REGION=${AWS_REGION:-eu-north-1}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - S3_ENDPOINT_URL=${S3_ENDPOINT_URL:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
    volumes:
      - ${LITRAG_DATA_DIR:-./data}:/app/data
      - ${LITRAG_INDICES_DIR:-./indices}:/app/indices
      - ${LITRAG_UPLOADS_DIR:-./uploads}:/app/uploads
      - ./config:/app/config:ro
    depends_on:
      - redis
    restart: unless-stopped
```

Add `redis_data:` under top-level `volumes:`. Add to the `api:` service env: `- REDIS_URL=${REDIS_URL:-redis://redis:6379/0}` and `depends_on: [redis]`.
**Check first whether `api:` uses `env_file: .env`** — if not, the explicit `environment:` list is the pattern; mirror it in `worker` (drop `env_file`).
- [ ] **Step 3:** Dockerfile CMD → `CMD ["python", "-m", "uvicorn", "literature_rag.api:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]`
- [ ] **Step 4:** `docker compose config --quiet` → exit 0. Full local suite green.
- [ ] **Step 5:** Commit `chore: redis + rq worker services, 2 uvicorn workers`.

---

### Task 2: `job_tasks.py` — extract ingestion into an rq-runnable function

**Files:** Create `literature_rag/job_tasks.py`; Modify `routers/jobs.py` (`upload_to_job` body); Test `tests/test_job_tasks.py`.

**Interfaces:** Produces `process_job_upload(task_id: str, job_id: int, tmp_path: str, phase: str, topic: str, original_filename: str) -> dict`. It: loads the Job, runs the SAME ingestion the sync route runs today, updates `UploadTaskRecord` (`status: processing→completed/failed`, `progress`, `result_json`/`error`), deletes `tmp_path`, returns the result dict.

- [ ] **Step 1:** Read `upload_to_job` fully (`sed -n '1295,1420p' literature_rag/routers/jobs.py`). Move its post-validation body (temp-file handling through indexing and DB writes — everything after ownership/quota checks) into `job_tasks.process_job_upload`, parameterized as above. Import inside the function what's needed (`get_job_collection`, extractor, indexer, storage) to avoid import cycles: `from .routers.jobs import get_job_collection` is legal at call time.
- [ ] **Step 2:** Rewrite the sync route to: validate → save upload to `/app/uploads/tmp/{uuid}_{filename}` (or `./uploads/tmp` when not in container: `Path(os.getenv("UPLOADS_DIR", "./uploads"))/"tmp"`) → create `UploadTaskRecord` via `UploadTaskCRUD.create` → call `process_job_upload(...)` **inline** (synchronous behavior preserved) → return its result. The sync route becomes a thin wrapper over the same function the queue runs.
- [ ] **Step 3:** Test (no network: monkeypatch the ingestion internals):

```python
"""process_job_upload updates UploadTaskRecord through the lifecycle."""
from unittest.mock import patch


def test_process_job_upload_marks_completed(tmp_path):
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD, UploadTaskCRUD
    from literature_rag import job_tasks

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="qtask@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="q-job")
    f = tmp_path / "doc.pdf"; f.write_bytes(b"%PDF-1.4 fake")
    UploadTaskCRUD.create(db, task_id="t1", filename="doc.pdf", phase="P1",
                          topic="T", status="queued", temp_file_path=str(f))

    with patch.object(job_tasks, "_ingest_pdf_to_job",
                      return_value={"success": True, "doc_id": "d1", "chunks_indexed": 3}):
        out = job_tasks.process_job_upload("t1", job.id, str(f), "P1", "T", "doc.pdf")

    assert out["success"] is True
    rec = UploadTaskCRUD.get_by_task_id(get_db_session(), "t1")
    assert rec.status == "completed" and rec.progress == 100
    assert not f.exists()  # temp cleaned


def test_process_job_upload_marks_failed(tmp_path):
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD, UploadTaskCRUD
    from literature_rag import job_tasks

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="qtask2@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="q-job2")
    f = tmp_path / "bad.pdf"; f.write_bytes(b"nope")
    UploadTaskCRUD.create(db, task_id="t2", filename="bad.pdf", phase="P1",
                          topic="T", status="queued", temp_file_path=str(f))

    with patch.object(job_tasks, "_ingest_pdf_to_job", side_effect=RuntimeError("boom")):
        out = job_tasks.process_job_upload("t2", job.id, str(f), "P1", "T", "bad.pdf")

    assert out["success"] is False
    rec = UploadTaskCRUD.get_by_task_id(get_db_session(), "t2")
    assert rec.status == "failed" and "boom" in (rec.error or "")
```

So `job_tasks.py` structure: `_ingest_pdf_to_job(job, tmp_path, phase, topic, original_filename) -> dict` (the moved body) and `process_job_upload(...)` (record lifecycle wrapper with try/except, calls `_ingest_pdf_to_job`, always cleans tmp file).
- [ ] **Step 4:** Suite green (existing upload E2E behavior unchanged — sync route wraps the same code). Commit `refactor: extract job ingestion into queue-runnable job_tasks module`.

---

### Task 3: Async endpoint + queue wiring

**Files:** Modify `routers/jobs.py` (new route), `literature_rag/api.py` only if the status route rejects job tasks (verify: `GET /api/upload/{task_id}/status` reads `UploadTaskRecord` by task_id — job-agnostic → no change). Test `tests/test_job_upload_async.py`.

- [ ] **Step 1:** New route in jobs.py (after the sync one):

```python
@router.post("/{job_id}/upload/async")
async def upload_to_job_async(
    job_id: int,
    file: UploadFile = File(...),
    phase: str = Form(...),
    topic: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enqueue a PDF for background indexing; poll /api/upload/{task_id}/status."""
    import uuid as _uuid
    job = JobCRUD.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    staging = Path(os.getenv("UPLOADS_DIR", "./uploads")) / "tmp"
    staging.mkdir(parents=True, exist_ok=True)
    task_id = _uuid.uuid4().hex[:16]
    tmp_path = staging / f"{task_id}_{Path(file.filename).name}"
    with open(tmp_path, "wb") as fh:
        fh.write(await file.read())

    from ..database import UploadTaskCRUD
    UploadTaskCRUD.create(db, task_id=task_id, filename=file.filename,
                          phase=phase, topic=topic, status="queued",
                          temp_file_path=str(tmp_path))

    from ..worker import WorkerManager
    from ..job_tasks import process_job_upload
    try:
        WorkerManager(backend="auto").enqueue(
            process_job_upload, task_id, job.id, str(tmp_path),
            phase, topic, file.filename, job_id=task_id)
    except Exception as e:
        logger.warning(f"Queue unavailable ({e}); processing inline")
        process_job_upload(task_id, job.id, str(tmp_path), phase, topic, file.filename)

    return {"task_id": task_id, "status_url": f"/api/upload/{task_id}/status"}
```

**Verify `WorkerManager.enqueue` signature** (worker.py:326) — pass `job_id=` only if supported; otherwise drop it.
- [ ] **Step 2:** Verify the status route: `grep -n "upload/{task_id}/status" -A 20 literature_rag/api.py` — confirm it reads `UploadTaskCRUD.get_by_task_id` and requires no ownership tie to global uploads. If it 404s on unknown fields, adapt response mapping only.
- [ ] **Step 3:** Test via TestClient (fake queue → runs inline path):

```python
"""Async job upload enqueues (or inlines) and is pollable via status route."""
from unittest.mock import patch
from fastapi.testclient import TestClient


def test_async_upload_returns_task_and_status(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    from literature_rag.api import app
    client = TestClient(app)
    r = client.post("/api/auth/register", json={
        "email": "async@test.local", "password": "Passw0rd!x", "name": "A"})
    tok = r.json().get("access_token") or client.post("/api/auth/login", json={
        "email": "async@test.local", "password": "Passw0rd!x"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    jid = client.post("/api/jobs", json={"name": "async-kb"}, headers=h).json()["id"]

    with patch("literature_rag.job_tasks._ingest_pdf_to_job",
               return_value={"success": True, "doc_id": "d", "chunks_indexed": 1}):
        r = client.post(f"/api/jobs/{jid}/upload/async", headers=h,
                        files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                        data={"phase": "P1", "topic": "T"})
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]
    s = client.get(f"/api/upload/{task_id}/status", headers=h)
    assert s.status_code == 200
    assert s.json().get("status") in ("queued", "processing", "completed")
```

(Without REDIS_URL, `WorkerManager("auto")` uses InMemoryWorker → runs promptly, or the except-inline path fires; both end in a DB record the status route sees.)
- [ ] **Step 4:** Suite green. Commit `feat: async per-job upload via rq queue with DB-backed status polling`.

---

### Task 4: Redis-backed rate limiting

**Files:** Modify `literature_rag/rate_limiter.py`; Test `tests/test_rate_limit_redis.py`.

- [ ] **Step 1:** Add after `SlidingWindowCounter`:

```python
class RedisFixedWindowCounter:
    """Fixed-window counter on Redis (INCR + EXPIRE). Cross-process safe.
    Slightly coarser than the sliding window; acceptable for API limits."""

    def __init__(self, redis_client, window_seconds: int = 60, prefix: str = "rl"):
        self._redis = redis_client
        self.window_seconds = window_seconds
        self._prefix = prefix

    def _key(self, client_id: str) -> str:
        import time
        window = int(time.time() // self.window_seconds)
        return f"{self._prefix}:{client_id}:{window}"

    def increment(self, client_id: str) -> int:
        key = self._key(client_id)
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window_seconds * 2)
        return int(pipe.execute()[0])

    def get_count(self, client_id: str) -> int:
        val = self._redis.get(self._key(client_id))
        return int(val) if val else 0

    def reset(self, client_id: str) -> None:
        self._redis.delete(self._key(client_id))
```

In `RateLimiter.__init__`, where counters are created (read lines 106-130 first): if `os.getenv("REDIS_URL")`, try `redis.Redis.from_url(...)` + `ping()`, use `RedisFixedWindowCounter(window_seconds=...)` for each counter; on any exception fall back to `SlidingWindowCounter` with a warning. Preserve constructor signature.
- [ ] **Step 2:** Test with a duck-typed fake redis (no new dep):

```python
class FakeRedis:
    def __init__(self): self.store = {}
    def pipeline(self): return FakePipe(self.store)
    def get(self, k): return self.store.get(k)
    def delete(self, k): self.store.pop(k, None)
    def ping(self): return True

class FakePipe:
    def __init__(self, store): self.store = store; self.ops = []
    def incr(self, k): self.ops.append(("incr", k)); return self
    def expire(self, k, s): self.ops.append(("expire", k)); return self
    def execute(self):
        out = []
        for op, k in self.ops:
            if op == "incr":
                self.store[k] = int(self.store.get(k, 0)) + 1
                out.append(self.store[k])
            else:
                out.append(True)
        return out


def test_redis_counter_increments_and_resets():
    from literature_rag.rate_limiter import RedisFixedWindowCounter
    c = RedisFixedWindowCounter(FakeRedis(), window_seconds=60)
    assert c.increment("ip1") == 1
    assert c.increment("ip1") == 2
    assert c.get_count("ip1") == 2
    c.reset("ip1")
    assert c.get_count("ip1") == 0
    assert c.increment("ip2") == 1  # isolation
```

- [ ] **Step 3:** Existing rate-limit tests must still pass (they run without REDIS_URL → in-memory path). Suite green. Commit `feat: Redis-backed rate limiting when REDIS_URL is set`.

---

### Task 5: Frontend async upload (contract-preserving)

**Files:** Modify `webapp/src/lib/api.ts` (~line 1040-1075 job upload method).

- [ ] **Step 1:** Read the current method; keep name/signature/return type. New body: POST to `/api/jobs/${jobId}/upload/async`; then poll `GET /api/upload/${task_id}/status` every 1.5s (cap ~10 min); on `completed` resolve with `result_json`-derived object matching the old response shape; on `failed` throw with the record's error. Report coarse progress via the existing progress callback if one exists (map queued→10, processing→50+record.progress/2, completed→100).
- [ ] **Step 2:** `npm run lint && npm run build` in webapp/ → green. Commit `feat: job uploads use async queue endpoint with status polling`.

---

### Task 6: Deploy + verify

- [ ] **Step 1:** Push; server `git pull && docker compose up -d --build api worker redis`. Wait healthz.
- [ ] **Step 2:** Verify services: `docker ps` shows lit-rag-redis, lit-rag-worker up; api logs show "OAuth state store: Redis" and rate-limiter Redis line; `docker logs lit-rag-worker` shows rq listening on literature_rag.
- [ ] **Step 3:** E2E async on prod: register temp user → create KB → POST `/upload/async` with smoke PDF → poll status to `completed` → query returns chunk → **verify the WORKER processed it** (`docker logs lit-rag-worker | grep <task_id or doc>`). Clean up temp user (SQL, as before).
- [ ] **Step 4:** Ship rebuilt frontend `dist/*` to `/var/www/humbowo` + chown.
- [ ] **Step 5:** Living docs + plan checkboxes; commit; push.

## Self-review
- ROADMAP Phase 2 item 3 (queue: Tasks 1-3,5,6), item 4 (Redis rate-limit Task 4; OAuth state free via REDIS_URL; multi-worker Task 1 Step 3). Chroma cleanup deliberately deferred until pgvector soak period passes.
- Crash-safety honesty: rq default is at-most-once (no acks_late equivalent by default) — a worker killed mid-task leaves the DB record in `processing`; acceptable for v1 because status is inspectable and re-upload is cheap. Noted as future hardening (rq `job_timeout` + requeue script) rather than pretending Celery-grade semantics.
- Sync route preserved; frontend contract preserved (polling hidden inside api.ts).
