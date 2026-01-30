# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Literature Review RAG System - Academic literature search system for 86 PDFs on German regional economic transitions. Adapted from a personality RAG system that achieved 100% MBTI accuracy with 15ms query speed.

## Essential Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Build/rebuild the index (processes 86 PDFs, takes 15-45 minutes)
python scripts/build_index.py

# Clear and rebuild index
rm -rf indices/* && python scripts/build_index.py

# Start API server
uvicorn literature_rag.api:app --host 0.0.0.0 --port 8001

# Test query endpoint
curl -X POST http://localhost:8001/query -H "Content-Type: application/json" -d '{"query": "business formation Ruhr", "n_results": 5}'

# Test papers filter
curl "http://localhost:8001/papers?topic_filter=Business%20Formation"

# Health check
curl http://localhost:8001/health
```

## Architecture

### Core Components

1. **`literature_rag/literature_rag.py`** - Core RAG engine with term normalization (the "secret sauce")
   - `normalize_query()` expands academic terms (e.g., "ruhrgebiet" → "ruhr valley", "ruhr region")
   - `query()` performs semantic search with metadata filtering
   - `get_context()` returns LLM-ready formatted context with citations

2. **`literature_rag/api.py`** - FastAPI server with 9 endpoints
   - `/query` - Semantic search with filters (phase_filter, topic_filter, year_min, year_max)
   - `/context` - LLM-ready context with citations
   - `/synthesis` - Multi-topic queries
   - `/papers` - List papers with filters
   - `/related` - Find similar papers by embedding

3. **`literature_rag/pdf_extractor.py`** - PDF processing with section detection
   - Extracts metadata from filename patterns (e.g., "2012_Thelen_Varieties.pdf" → year=2012, author=Thelen)
   - Section-aware extraction (abstract, methods, results, conclusion)
   - Falls back to full-text extraction if section detection fails

4. **`scripts/build_index.py`** - Index builder with hierarchical chunking
   - Parent chunks (2048 chars) for broader context
   - Child chunks (1024 chars) for precise retrieval
   - Links parent/child via `parent_id` metadata

### Key Design Patterns

- **Term Normalization**: Defined in `config/literature_config.yaml` under `normalization.term_maps`. Maps academic term variants (e.g., "NRW" ↔ "North Rhine-Westphalia").

- **Hierarchical Chunking**: Creates parent (2048 chars) and child (1024 chars) chunks with `hierarchy_level` and `parent_id` metadata fields.

- **ChromaDB Metadata Constraints**: All metadata values must be str, int, float, or bool. Lists are converted to comma-separated strings. None values are excluded.

### Data Flow

```
PDFs → pdf_extractor.py (extract + metadata) → build_index.py (chunk + embed) → ChromaDB
                                                                                    ↓
User Query → api.py → literature_rag.py (normalize + search) → ChromaDB → Results
```

## Configuration

- **`config/literature_config.yaml`** - Main configuration (chunking, embedding, term maps, API settings)
- **`.env`** - Environment overrides (PDF_PATH, API_PORT, API_KEY, DEVICE)

## Dependencies

Uses Python 3.12 (not 3.14 due to package compatibility). Key packages:
- `chromadb==0.4.24` (pinned for NumPy 1.x compatibility)
- `numpy<2.0.0` (required for ChromaDB 0.4.24)
- `langchain-text-splitters` (not `langchain.text_splitter`)

## API Parameter Names

Filter parameters use `_filter` suffix for consistency:
- `phase_filter` (not `phase`)
- `topic_filter` (not `topic`)
