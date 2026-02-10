from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from aurora_kernel.corpus_loader import load_corpus
from aurora_kernel.elastic_store import make_es_client, index_corpus

def main() -> int:
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="Path to corpus repo root")
    ap.add_argument("--index", default=os.getenv("AURORA_INDEX", "aurora_corpus_v0"))
    args = ap.parse_args()

    cloud_id = os.getenv("ELASTIC_CLOUD_ID")
    es_url = os.getenv("ES_URL")
    api_key = os.getenv("ES_API_KEY")
    username = os.getenv("ES_USERNAME")
    password = os.getenv("ES_PASSWORD")

    client = make_es_client(cloud_id=cloud_id, es_url=es_url, api_key=api_key, username=username, password=password)

    corpus = Path(args.corpus).resolve()
    docs = load_corpus(corpus)

    resp = index_corpus(client, index=args.index, docs=docs)
    print(resp)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
