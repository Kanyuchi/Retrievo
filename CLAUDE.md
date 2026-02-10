# Literature Review RAG - Claude Context

## Workflow Rules

### Auto-Commit Policy
**IMPORTANT:** After making any file changes (edits, additions, or deletions), Claude MUST:
1. Stage the changed files with `git add <specific-files>`
2. Commit with a descriptive message
3. Push to origin/main

**Commit Message Format:** Use regular commit messages without Co-Authored-By attribution.

This ensures all changes are tracked in version control automatically without requiring explicit user requests.

### Iterative Problem Resolution
**IMPORTANT:** When confronted with any bug, integration issue, or system problem:
1. Diagnose the root cause — read the relevant code, check logs, test endpoints
2. Implement the fix immediately without asking for permission
3. Verify the fix works end-to-end (test both backend API and frontend behavior)
4. If the fix doesn't resolve the issue, iterate: re-diagnose, re-fix, re-verify
5. Continue iterating until the problem is fully resolved
6. Never leave a problem half-fixed or tell the user to "try restarting" — verify it yourself

Claude is an expert in frontend (React/TypeScript), backend (FastAPI/Python), system architecture, and full-stack integration. Apply that expertise proactively.

### Multi-User Production System
**CRITICAL:** This system is deployed in PRODUCTION on AWS with real users testing it.

**ALL new features, enhancements, and bug fixes MUST support:**
1. **User Knowledge Bases (Jobs)** - Each user has isolated knowledge bases via `/api/jobs/{id}/`
2. **Default Knowledge Base** - Shared collection for all users via `/api/upload`, `/api/search`
3. **AWS S3 Storage** - PDFs are stored in S3, not local filesystem

**When implementing ANY feature:**
- Apply to BOTH default knowledge base AND user knowledge bases (jobs)
- Test with job-scoped endpoints (`/api/jobs/{id}/upload`, `/api/jobs/{id}/query`, etc.)
- Ensure S3 storage compatibility
- Never implement features only for the default collection

**Architecture:**
- Default KB: `literature_review_chunks` collection, shared BM25 index
- User KBs: `job_{id}_{uuid}` collections, per-job BM25 indices (`bm25_job_{id}.pkl`)
- Storage: AWS S3 bucket for all PDF files
- Database: SQLite/PostgreSQL for user, job, and document metadata

---

## Project Overview
Academic literature RAG system for German regional economic transitions research. Contains 13,578 chunks from 83 papers indexed with BAAI/bge-base-en-v1.5 embeddings in ChromaDB.

## Key Paths
- **API Code**: `literature_review_rag_api/literature_rag/`
- **MCP Server**: `literature_review_rag_api/literature_rag/mcp_server.py`
- **Config**: `literature_review_rag_api/config/literature_config.yaml`
- **Indices**: `literature_review_rag_api/indices/`
- **Virtual Env**: `literature_review_rag_api/venv/`

## MCP Server Tools
The `literature-rag` MCP server exposes 7 tools:
- `semantic_search` - Search with filters (phase, topic, year)
- `get_context_for_llm` - Formatted context with citations
- `list_papers` - List available papers
- `find_related_papers` - Find similar papers by embedding
- `get_collection_stats` - Collection statistics
- `answer_with_citations` - Sources with bibliography
- `synthesis_query` - Multi-topic comparative analysis

## Running the MCP Server
```bash
cd /Users/fadzie/Desktop/lit_rag/literature_review_rag_api
source venv/bin/activate
python -m literature_rag.mcp_server
```

## Running the FastAPI Server
```bash
cd /Users/fadzie/Desktop/lit_rag/literature_review_rag_api
source venv/bin/activate
python -m literature_rag.api
```
API runs on http://localhost:8001

---

## Production Deployment

### SSH Key Location
**IMPORTANT:** The SSH key for production server is stored at:
```
.keys/lightsail.pem
```

This key is gitignored and must NEVER be committed. Always use this key when deploying.

### Production Server
- **Host**: `13.49.191.201`
- **User**: `ubuntu`
- **App Directory**: `~/lit-rag-api`

### Deploy Backend
```bash
ssh -i .keys/lightsail.pem ubuntu@13.49.191.201 "cd lit-rag-api && git pull origin main && docker compose down && docker compose up -d --build"
```

### Deploy Frontend
```bash
cd webapp && npm run build
scp -i .keys/lightsail.pem -r dist/* ubuntu@13.49.191.201:~/lit-rag-api/webapp-dist/
```

### View Logs
```bash
ssh -i .keys/lightsail.pem ubuntu@13.49.191.201 "cd lit-rag-api && docker compose logs -f --tail=100"
```

---

## Dependency Management Rule

**IMPORTANT:** When a process requires credentials, keys, or configuration files:
1. Store them in a predictable project location (e.g., `.keys/`, `.config/`)
2. Add to `.gitignore` to prevent accidental commits
3. Document the location in this file
4. Use the stored dependency automatically without asking the user each time

This applies to: SSH keys, API keys, certificates, configuration files, and any other dependencies needed for automated processes
