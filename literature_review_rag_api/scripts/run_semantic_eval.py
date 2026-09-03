"""Semantic retrieval eval against a live Humbowo knowledge base.

Corpus-agnostic: expectations reference ORIGINAL FILENAMES (substring match),
which are resolved to doc_ids via the job's document list — so the same
queries file works after any re-upload/re-index.

Usage:
  python scripts/run_semantic_eval.py --base-url https://humbowo.com \
      --email you@x.com --password ... --job-id 7 \
      --queries eval/demo_queries.yaml [--k 5] [--min-precision 0.6]

Queries YAML:
  queries:
    - id: q1
      query: "coal phase-out employment effects"
      expected_files: ["ruhr_transition"]   # substring of original_filename
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

import yaml


def _post(base, path, body, token=None):
    req = urllib.request.Request(
        base + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {})})
    return json.load(urllib.request.urlopen(req, timeout=60))


def _get(base, path, token, params=None):
    qs = ("?" + urllib.parse.urlencode(params)) if params else ""
    req = urllib.request.Request(
        base + path + qs, headers={"Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--job-id", type=int, required=True)
    ap.add_argument("--queries", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--min-precision", type=float, default=0.0)
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    token = _post(base, "/api/auth/login",
                  {"email": args.email, "password": args.password})["access_token"]

    docs = _get(base, f"/api/jobs/{args.job_id}/documents", token)
    doc_list = docs.get("documents", docs if isinstance(docs, list) else [])
    file_by_doc = {d["doc_id"]: (d.get("original_filename") or d.get("filename") or "")
                   for d in doc_list}
    print(f"corpus: {len(file_by_doc)} documents")

    spec = yaml.safe_load(open(args.queries))
    queries = spec["queries"]

    total_p, total_r, total_mrr, judged = 0.0, 0.0, 0.0, 0
    for q in queries:
        expected = [e.lower() for e in q.get("expected_files", [])]
        if not expected:
            continue
        res = _get(base, f"/api/jobs/{args.job_id}/query", token,
                   {"question": q["query"], "n_sources": args.k})
        hits_docs = []
        seen = set()
        for r in res.get("results", []):
            did = (r.get("metadata") or {}).get("doc_id")
            if did and did not in seen:
                seen.add(did)
                hits_docs.append(file_by_doc.get(did, "").lower())

        import re

        def _norm(t):
            return re.sub(r"[^a-z0-9]+", "_", t.lower())

        def _match(fname):
            nf = _norm(fname)
            return any(_norm(e) in nf for e in expected)

        rel = [i for i, f in enumerate(hits_docs) if _match(f)]
        matched_files = {e for e in expected
                         if any(_norm(e) in _norm(f) for f in hits_docs)}
        p = len(rel) / len(hits_docs) if hits_docs else 0.0
        r_ = len(matched_files) / len(expected)
        mrr = 1.0 / (rel[0] + 1) if rel else 0.0
        total_p += p; total_r += r_; total_mrr += mrr; judged += 1
        flag = "OK " if r_ == 1.0 else ("MISS" if not rel else "part")
        print(f"[{flag}] {q['id']}: P@{args.k}={p:.2f} recall={r_:.2f} mrr={mrr:.2f} | {q['query'][:60]}")

    if not judged:
        print("no judged queries"); return 1
    ap_, ar, amrr = total_p / judged, total_r / judged, total_mrr / judged
    print(f"\nAGGREGATE over {judged} queries: precision={ap_:.3f} recall={ar:.3f} MRR={amrr:.3f}")
    if ap_ < args.min_precision:
        print(f"FAIL: precision {ap_:.3f} < gate {args.min_precision}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
