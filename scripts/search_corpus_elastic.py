from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

from aurora_kernel.elastic_store import make_es_client, search

def main() -> int:
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True)
    ap.add_argument("--index", default=os.getenv("AURORA_INDEX", "aurora_corpus_v0"))
    ap.add_argument("--doc_type", default=None)
    ap.add_argument("--stakeholder", default=None)
    ap.add_argument("--jurisdiction", default=None)
    args = ap.parse_args()

    cloud_id = os.getenv("ELASTIC_CLOUD_ID")
    es_url = os.getenv("ES_URL")
    api_key = os.getenv("ES_API_KEY")
    username = os.getenv("ES_USERNAME")
    password = os.getenv("ES_PASSWORD")

    client = make_es_client(cloud_id=cloud_id, es_url=es_url, api_key=api_key, username=username, password=password)

    filters = {"doc_type": args.doc_type, "stakeholder": args.stakeholder, "jurisdiction": args.jurisdiction}
    resp = search(client, index=args.index, q=args.q, filters=filters, size=8)
    print(resp)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
