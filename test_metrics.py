"""
Test script for metrics logging system.
Run this after starting the backend to verify DB logging works.
"""

import requests
import json
import time

API_URL = "http://localhost:8000"


def test_metrics_logging():
    """Test the complete metrics logging pipeline."""
    
    print("🧪 Testing PaperStack Metrics Logging\n")
    
    # Step 1: Create session
    print("1️⃣ Creating session...")
    response = requests.post(
        f"{API_URL}/session/create",
        json={"initial_query": "Test metrics logging"}
    )
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"   ✓ Session created: {session_id}\n")
    
    # Step 2: Search papers
    print("2️⃣ Searching papers...")
    response = requests.post(
        f"{API_URL}/brain/search",
        json={
            "session_id": session_id,
            "query": "attention mechanism transformers",
            "search_mode": "topic"
        }
    )
    search_data = response.json()
    papers = search_data.get("papers", [])
    print(f"   ✓ Found {len(papers)} papers\n")
    
    if not papers:
        print("❌ No papers found. Cannot test chat.")
        return
    
    # Step 3: Load papers
    print("3️⃣ Loading first paper...")
    paper_ids = [papers[0]["arxiv_id"]]
    response = requests.post(
        f"{API_URL}/brain/load",
        json={
            "session_id": session_id,
            "paper_ids": paper_ids
        }
    )
    load_data = response.json()
    print(f"   ✓ Loaded: {load_data.get('loaded_papers', [])}\n")
    
    # Step 4: Send chat message (THIS LOGS METRICS)
    print("4️⃣ Sending chat message...")
    response = requests.post(
        f"{API_URL}/chat/message",
        json={
            "session_id": session_id,
            "message": "What is the main contribution?"
        }
    )
    chat_data = response.json()
    print(f"   ✓ Answer received: {chat_data['answer'][:100]}...\n")
    
    # Give async logging time to complete
    print("⏳ Waiting for async logging to complete...")
    time.sleep(2)
    
    # Step 5: Verify DB entries
    print("\n5️⃣ Verifying database entries...")
    verify_database(session_id)
    
    print("\n✅ Test complete!")


def verify_database(session_id):
    """Verify that metrics were logged to database."""
    from backend.db import repository
    
    # Check requests
    requests_data = repository.get_requests_by_session(session_id)
    print(f"   📊 Requests logged: {len(requests_data)}")
    
    if requests_data:
        req = requests_data[0]
        print(f"   - Query: {req['query']}")
        print(f"   - Prompt tokens: {req['prompt_tokens']}")
        print(f"   - Chunk tokens: {req['total_chunk_tokens']}")
        print(f"   - Completion tokens: {req['completion_tokens']}")
        print(f"   - LLM latency: {req['llm_latency_ms']:.2f}ms")
        print(f"   - Total latency: {req['total_latency_ms']:.2f}ms")
        
        # Check chunks
        chunks = repository.get_chunks_by_request(req['request_id'])
        print(f"\n   📄 Chunks logged: {len(chunks)}")
        if chunks:
            for i, chunk in enumerate(chunks[:3], 1):
                print(f"   - Chunk {i}: {chunk['paper_title']} ({chunk['chunk_token_count']} tokens)")
    
    # Check session metrics
    metrics = repository.get_session_metrics(session_id)
    if metrics.get('total_requests'):
        print(f"\n   📈 Session Metrics:")
        print(f"   - Total requests: {metrics['total_requests']}")
        print(f"   - Avg LLM latency: {metrics['avg_llm_latency']:.2f}ms")
        print(f"   - Total tokens: {metrics['total_tokens']}")


if __name__ == "__main__":
    test_metrics_logging()
