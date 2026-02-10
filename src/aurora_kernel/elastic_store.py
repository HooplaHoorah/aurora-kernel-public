from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch

from aurora_kernel.corpus_loader import CorpusDoc
from aurora_kernel.chunker import chunk_text

def make_es_client(cloud_id: Optional[str] = None, es_url: Optional[str] = None, api_key: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None) -> Elasticsearch:
    # Cloud ID with Basic Auth
    if cloud_id and username and password:
        return Elasticsearch(cloud_id=cloud_id, basic_auth=(username, password))
    # Cloud ID with API Key
    if cloud_id and api_key:
        return Elasticsearch(cloud_id=cloud_id, api_key=api_key)
    # URL with API Key
    if es_url and api_key:
        return Elasticsearch(es_url, api_key=api_key)
    # URL with Basic Auth
    if es_url and username and password:
        return Elasticsearch(es_url, basic_auth=(username, password))
    # URL only
    if es_url:
        return Elasticsearch(es_url)
    # Fallback to localhost
    return Elasticsearch("http://localhost:9200")

def ensure_index(client: Elasticsearch, index: str) -> None:
    if client.indices.exists(index=index):
        return

    mapping = {
        "mappings": {
            "properties": {
                "doc_id": {"type": "keyword"},
                "doc_type": {"type": "keyword"},
                "stakeholder": {"type": "keyword"},
                "system": {"type": "keyword"},
                "jurisdiction": {"type": "keyword"},
                "control_ids": {"type": "keyword"},
                "date": {"type": "keyword"},
                "title": {"type": "text"},
                "content": {"type": "text"},
                "source_path": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "section": {"type": "keyword"},
            }
        }
    }
    client.indices.create(index=index, **mapping)

def index_corpus(client: Elasticsearch, index: str, docs: List[CorpusDoc]) -> Dict[str, Any]:
    ensure_index(client, index)

    ops: List[Dict[str, Any]] = []
    total_chunks = 0

    for d in docs:
        chunks = chunk_text(d.doc_id, d.body)
        for c in chunks:
            total_chunks += 1
            doc_body = {
                "doc_id": d.doc_id,
                "doc_type": d.doc_type,
                "stakeholder": d.stakeholder,
                "system": d.system,
                "jurisdiction": d.jurisdiction,
                "control_ids": d.control_ids,
                "date": d.date,
                "title": d.title,
                "content": c.text,
                "source_path": d.source_path,
                "chunk_id": c.chunk_id,
                "section": c.section,
            }
            ops.append({"index": {"_index": index, "_id": c.chunk_id}})
            ops.append(doc_body)

    if ops:
        resp = client.bulk(operations=ops, refresh=True)
        if hasattr(resp, "body"):
            resp = resp.body
        elif hasattr(resp, "meta"):
            # Some client versions
            resp = resp.body
    else:
        resp = {"items": []}

    return {"indexed_docs": len(docs), "indexed_chunks": total_chunks, "bulk": resp}

def search(client: Elasticsearch, index: str, q: str, filters: Optional[Dict[str, Any]] = None, size: int = 5) -> Dict[str, Any]:
    filters = filters or {}
    must_filters = []
    for key, value in filters.items():
        if value is None:
            continue
        if isinstance(value, list):
            must_filters.append({"terms": {key: value}})
        else:
            must_filters.append({"term": {key: value}})

    query = {
        "bool": {
            "must": [
                {"multi_match": {"query": q, "fields": ["content", "title", "doc_id", "doc_type"]}}
            ],
            "filter": must_filters
        }
    }

    resp = client.search(index=index, query=query, size=size, highlight={"fields": {"content": {}}})
    hits_out = []
    for h in resp.get("hits", {}).get("hits", []):
        src = h.get("_source", {})
        hits_out.append({
            "score": h.get("_score"),
            "doc_id": src.get("doc_id"),
            "doc_type": src.get("doc_type"),
            "stakeholder": src.get("stakeholder"),
            "jurisdiction": src.get("jurisdiction"),
            "control_ids": src.get("control_ids"),
            "title": src.get("title"),
            "content": src.get("content"),
            "source_path": src.get("source_path"),
            "chunk_id": src.get("chunk_id"),
            "section": src.get("section"),
            "highlights": h.get("highlight", {}),
        })

    return {"query": q, "filters": filters, "hits": hits_out}
