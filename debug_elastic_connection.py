"""
Elasticsearch Connection Diagnostic Script
===========================================
Run this first to identify the exact connection issue.

Usage:
    python debug_elastic_connection.py
"""

import os
import sys
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def main():
    print_header("Aurora Elasticsearch Connection Diagnostic")
    
    # Load environment variables
    load_dotenv()
    
    cloud_id = os.getenv("ELASTIC_CLOUD_ID")
    api_key = os.getenv("ES_API_KEY")
    username = os.getenv("ES_USERNAME")
    password = os.getenv("ES_PASSWORD")
    
    # Step 1: Verify environment variables
    print_header("Step 1: Environment Variables Check")
    
    if not cloud_id:
        print_error("ELASTIC_CLOUD_ID not found in .env")
        sys.exit(1)
    print_success(f"ELASTIC_CLOUD_ID found (length: {len(cloud_id)} chars)")
    print(f"  First 50 chars: {cloud_id[:50]}...")
    
    if api_key:
        print_success(f"ES_API_KEY found (length: {len(api_key)} chars)")
        print(f"  First 20 chars: {api_key[:20]}...")
    elif username and password:
        print_success(f"ES_USERNAME found: {username}")
        print_success("ES_PASSWORD found (hidden)")
    else:
        print_error("No authentication found (need ES_API_KEY or ES_USERNAME/ES_PASSWORD)")
        sys.exit(1)
    
    # Step 2: Test basic connection
    print_header("Step 2: Basic Connection Test")
    
    try:
        if api_key:
            print("Attempting connection with API Key...")
            client = Elasticsearch(
                cloud_id=cloud_id,
                api_key=api_key,
                request_timeout=30
            )
        else:
            print("Attempting connection with Basic Auth...")
            client = Elasticsearch(
                cloud_id=cloud_id,
                basic_auth=(username, password),
                request_timeout=30
            )
        
        print_success("Client object created successfully")
        
        # Test actual connection
        info = client.info()
        print_success("Connection successful!")
        print(f"  Cluster Name: {info['cluster_name']}")
        print(f"  Cluster UUID: {info['cluster_uuid']}")
        print(f"  Version: {info['version']['number']}")
        print(f"  Lucene Version: {info['version']['lucene_version']}")
        
    except Exception as e:
        print_error(f"Connection failed: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 3: List existing indices
    print_header("Step 3: List Existing Indices")
    
    try:
        indices = client.cat.indices(format='json')
        if indices:
            print_success(f"Found {len(indices)} existing indices:")
            for idx in indices:
                print(f"  - {idx['index']} (docs: {idx.get('docs.count', 'N/A')})")
        else:
            print_warning("No indices found (this is normal for a new cluster)")
    except Exception as e:
        print_error(f"Failed to list indices: {type(e).__name__}")
        print(f"  Message: {str(e)}")
    
    # Step 4: Test index creation
    print_header("Step 4: Test Index Creation")
    
    test_index = "aurora_diagnostic_test"
    
    try:
        # Check if test index already exists
        if client.indices.exists(index=test_index):
            print_warning(f"Test index '{test_index}' already exists, deleting...")
            client.indices.delete(index=test_index)
        
        # Create test index
        print(f"Creating test index: {test_index}")
        response = client.indices.create(
            index=test_index,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                },
                "mappings": {
                    "properties": {
                        "test_field": {"type": "text"}
                    }
                }
            }
        )
        print_success("Test index created successfully!")
        print(f"  Response: {response}")
        
        # Verify it exists
        exists = client.indices.exists(index=test_index)
        if exists:
            print_success(f"Verified: test index exists")
        else:
            print_error(f"Test index creation succeeded but exists() returned False")
        
        # Test document insertion
        print("\nTesting document insertion...")
        doc_response = client.index(
            index=test_index,
            body={"test_field": "Hello from Aurora!"},
            refresh=True
        )
        print_success("Document inserted successfully!")
        print(f"  Document ID: {doc_response['_id']}")
        
        # Test search
        print("\nTesting search...")
        search_response = client.search(index=test_index, body={"query": {"match_all": {}}})
        print_success(f"Search successful! Found {search_response['hits']['total']['value']} documents")
        
        # Clean up
        print("\nCleaning up test index...")
        client.indices.delete(index=test_index)
        print_success("Test index deleted")
        
    except Exception as e:
        print_error(f"Index creation/operations failed: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()
        
        # Try to clean up
        try:
            if client.indices.exists(index=test_index):
                client.indices.delete(index=test_index)
        except:
            pass
        
        print("\n" + "="*60)
        print("DIAGNOSTIC RESULT: Index creation failed")
        print("="*60)
        print("\nPossible causes:")
        print("1. API Key lacks 'create_index' privilege")
        print("2. API Key is restricted to specific index patterns")
        print("3. Elasticsearch client version incompatibility")
        print("4. Cloud ID format issue")
        print("\nNext steps:")
        print("- Try Solution 2: Fix API Key Privileges")
        print("- Try Solution 3: Use Basic Auth Instead")
        sys.exit(1)
    
    # Step 5: Test the actual Aurora index
    print_header("Step 5: Test Aurora Index Pattern")
    
    aurora_index = os.getenv("AURORA_INDEX", "aurora_hackathon_corpus_v1")
    print(f"Target index: {aurora_index}")
    
    try:
        if client.indices.exists(index=aurora_index):
            print_success(f"Index '{aurora_index}' already exists!")
            # Get index stats
            stats = client.indices.stats(index=aurora_index)
            doc_count = stats['_all']['total']['docs']['count']
            print(f"  Document count: {doc_count}")
        else:
            print_warning(f"Index '{aurora_index}' does not exist yet")
            print("  This is expected on first run - ingestion will create it")
            
            # Test if we can create it
            print(f"\nTesting creation of '{aurora_index}'...")
            response = client.indices.create(
                index=aurora_index,
                body={
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    }
                }
            )
            print_success(f"Successfully created '{aurora_index}'!")
            print("  You can now run the /ingest endpoint")
            
    except Exception as e:
        print_error(f"Failed to work with Aurora index: {type(e).__name__}")
        print(f"  Message: {str(e)}")
    
    # Final summary
    print_header("Diagnostic Summary")
    print_success("All tests passed! ✨")
    print("\nYour Elasticsearch connection is working correctly.")
    print("You should be able to use the /ingest endpoint now.")
    print("\nIf /ingest still fails, check:")
    print("  1. AURORA_INDEX environment variable matches the index name")
    print("  2. The corpus path is correct and contains valid YAML files")
    print("  3. Review the uvicorn logs for detailed error messages")

if __name__ == "__main__":
    main()
