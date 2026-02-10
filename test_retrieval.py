import os
from dotenv import load_dotenv
from aurora_kernel.elastic_store import make_es_client, search as es_search

load_dotenv()

def test_search():
    cloud_id = os.getenv("ELASTIC_CLOUD_ID")
    username = os.getenv("ES_USERNAME")
    password = os.getenv("ES_PASSWORD")
    index = os.getenv("AURORA_INDEX", "aurora_kb_v1")
    
    c = make_es_client(cloud_id=cloud_id, username=username, password=password)
    
    q = "What are the key requirements for account management in the FISMA policy?"
    print(f"Searching index '{index}' for: {q}")
    
    results = es_search(c, index=index, q=q, filters={}, size=5)
    
    print(f"Total hits: {len(results.get('hits', []))}")
    for i, hit in enumerate(results.get("hits", [])):
        print(f"\nHit {i+1} (Score: {hit.get('score')}):")
        print(f"Title: {hit.get('title')}")
        print(f"Content Snippet: {hit.get('content')[:200]}...")

if __name__ == "__main__":
    test_search()
