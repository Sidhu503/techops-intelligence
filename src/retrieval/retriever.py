"""
TechOps Intelligence Platform
Retrieval Layer — Hybrid Search + Reranking

Usage:
    from src.retrieval.retriever import retrieve, format_results

    results = retrieve(
        query        = "database connection refused",
        top_k_return = 3
    )
"""

import re
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import chromadb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMBEDDINGS   = PROJECT_ROOT / "data/embeddings"

# ── Model Loading ──────────────────────────────────────
_embedding_model = None
_cross_encoder   = None
_client          = None
_collections     = {}
_bm25_indices    = {}


def _load_models():
    global _embedding_model, _cross_encoder, _client
    global _collections, _bm25_indices

    if _embedding_model is not None:
        return

    _embedding_model = SentenceTransformer(
        "sentence-transformers/all-mpnet-base-v2",
        device="cpu"
    )
    _cross_encoder = CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device="cpu"
    )
    _client = chromadb.PersistentClient(
        path=str(EMBEDDINGS / "chroma_db")
    )

    for name in ["incidents", "postmortems", "playbooks",
                 "knowledge_base", "logs"]:
        try:
            _collections[name] = _client.get_collection(name)
        except Exception:
            pass

    for name, col in _collections.items():
        bm25, docs, ids = _build_bm25(col)
        if bm25:
            _bm25_indices[name] = {
                "bm25": bm25, "docs": docs, "ids": ids
            }


def _build_bm25(collection, batch_size=1000):
    count = collection.count()
    if count == 0:
        return None, [], []
    all_docs, all_ids = [], []
    offset = 0
    while offset < count:
        batch = collection.get(
            limit=batch_size, offset=offset,
            include=["documents"]
        )
        all_docs.extend(batch["documents"])
        all_ids.extend(batch["ids"])
        offset += batch_size
    tokenized = [_tokenize(d) for d in all_docs]
    return BM25Okapi(tokenized), all_docs, all_ids


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+(?:[_\-\.][a-z0-9]+)*",
                      text.lower())


ROUTING = {
    "incidents"     : ["incident","outage","down","failing",
                       "error","timeout","crashloop","degraded"],
    "postmortems"   : ["root cause","what caused","why did",
                       "postmortem","fix","similar","diagnosis"],
    "playbooks"     : ["playbook","runbook","how to respond",
                       "procedure","ransomware","phishing","ddos"],
    "knowledge_base": ["slo","sla","error budget","reliability",
                       "best practice","sre","troubleshoot",
                       "circuit breaker","on-call","escalation"],
    "logs"          : ["log","metric","cpu","memory","disk",
                       "swap","load","iowait","anomaly","spike"]
}


def _route(query: str) -> List[str]:
    q      = query.lower()
    scores = {
        col: sum(1 for kw in kws if kw in q)
        for col, kws in ROUTING.items()
        if col in _collections
    }
    scored = [c for c, s in scores.items() if s > 0]
    if not scored:
        return ["postmortems", "knowledge_base"]
    return sorted(scored, key=lambda x: scores[x], reverse=True)


def retrieve(
    query           : str,
    collection_names: Optional[List[str]] = None,
    top_k_fetch     : int   = 10,
    top_k_return    : int   = 3,
    bm25_weight     : float = 0.4,
    semantic_weight : float = 0.6,
    use_reranking   : bool  = True,
    filter_metadata : Optional[Dict] = None
) -> List[Dict]:
    _load_models()

    cols = (collection_names or _route(query))[:2]
    bm25_res, sem_res = [], []

    for col in cols:
        if col in _bm25_indices:
            idx    = _bm25_indices[col]
            tokens = _tokenize(query)
            scores = idx["bm25"].get_scores(tokens)
            top_i  = np.argsort(scores)[::-1][:top_k_fetch]
            for rank, i in enumerate(top_i, 1):
                if scores[i] > 0:
                    bm25_res.append({
                        "id": idx["ids"][i], "text": idx["docs"][i],
                        "score": float(scores[i]),
                        "source": "bm25", "rank": rank
                    })

        if col in _collections:
            emb = _embedding_model.encode([query]).tolist()
            kw  = {"query_embeddings": emb, "n_results": top_k_fetch,
                   "include": ["documents", "metadatas", "distances"]}
            if filter_metadata:
                kw["where"] = filter_metadata
            try:
                r = _collections[col].query(**kw)
                for rank, (doc, meta, dist) in enumerate(zip(
                    r["documents"][0], r["metadatas"][0],
                    r["distances"][0]
                ), 1):
                    sem_res.append({
                        "id": r["ids"][0][rank-1], "text": doc,
                        "score": float(1 - dist), "metadata": meta,
                        "source": "semantic", "rank": rank
                    })
            except Exception:
                pass

    if not bm25_res and not sem_res:
        return []

    # RRF merge
    k=60
    fused, all_d = {}, {}
    for item in bm25_res:
        fused[item["id"]] = fused.get(item["id"],0) + bm25_weight/(k+item["rank"])
        all_d[item["id"]] = item
    for item in sem_res:
        fused[item["id"]] = fused.get(item["id"],0) + semantic_weight/(k+item["rank"])
        if item["id"] not in all_d:
            all_d[item["id"]] = item

    candidates = [
        {**all_d[id_], "rrf_score": s, "rank": r}
        for r, (id_, s) in enumerate(
            sorted(fused.items(), key=lambda x: -x[1]), 1
        )
    ][:top_k_fetch]

    if use_reranking and candidates:
        pairs  = [(query, c["text"][:512]) for c in candidates]
        rscores = _cross_encoder.predict(pairs)
        for c, s in zip(candidates, rscores):
            c["rerank_score"] = float(s)
        candidates = sorted(
            candidates, key=lambda x: x["rerank_score"], reverse=True
        )[:top_k_return]
        for i, c in enumerate(candidates, 1):
            c["final_rank"] = i

    return candidates[:top_k_return]


def format_results(results: List[Dict]) -> str:
    if not results:
        return "No relevant documents found."
    parts = []
    for i, r in enumerate(results, 1):
        score = r.get("rerank_score", r.get("rrf_score", 0))
        meta  = r.get("metadata", {})
        src   = meta.get("source", r.get("source", "unknown"))
        parts.append(
            f"Result {i} (score: {score:.3f}, source: {src}):\n"
            f"{r['text'][:400]}"
        )
    return "\n\n---\n\n".join(parts)
