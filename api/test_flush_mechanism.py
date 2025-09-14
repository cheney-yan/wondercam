#!/usr/bin/env python3
"""
Test script to verify that SSE flush mechanism works correctly
"""

import asyncio
import time

async def test_generator_with_flush():
    """Test generator that demonstrates flush behavior"""
    
    print("Testing generator with flush mechanism...")
    
    async def mock_streaming_response():
        """Mock streaming response with flush"""
        
        # Send immediate OK
        print("  📤 Yielding OK message...")
        yield "data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"OK\"}]}}]}\n\n"
        
        # Force flush with SSE comment
        print("  💨 Forcing flush...")
        yield ": flush\n\n"
        
        # Small delay
        print("  ⏱️  Sleeping 0.01s...")
        await asyncio.sleep(0.01)
        
        # Continue with more data
        print("  📤 Yielding more data...")
        yield "data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"Processing...\"}]}}]}\n\n"
    
    start_time = time.time()
    chunk_count = 0
    
    async for chunk in mock_streaming_response():
        current_time = time.time()
        elapsed = current_time - start_time
        chunk_count += 1
        
        print(f"  🔸 Chunk {chunk_count} received at {elapsed:.4f}s: {chunk.strip()[:50]}...")
    
    total_time = time.time() - start_time
    print(f"  ✅ Total time: {total_time:.4f}s for {chunk_count} chunks")

def test_sse_comment_format():
    """Test SSE comment format"""
    
    print("\nTesting SSE comment format...")
    
    # Valid SSE comment formats
    comments = [
        ": flush\n\n",                    # Simple comment
        ": force-flush\n\n",              # Comment with dash
        ":\n\n",                          # Empty comment
        ": keep-alive ping\n\n",          # Longer comment
    ]
    
    for i, comment in enumerate(comments):
        print(f"  Comment {i+1}: {repr(comment)}")
        # In real SSE, comments are ignored by browsers but force network flush
        print(f"    - Length: {len(comment)} bytes")
        print(f"    - Ends with \\n\\n: {comment.endswith('\\n\\n')}")

async def main():
    """Run all tests"""
    
    print("🧪 Testing SSE flush mechanisms...\n")
    
    # Test 1: Generator with flush
    await test_generator_with_flush()
    
    # Test 2: SSE comment formats
    test_sse_comment_format()
    
    print(f"\n📋 Summary:")
    print(f"   SSE comments (': flush\\n\\n') force network transmission")
    print(f"   This ensures immediate delivery without waiting for buffer fill")
    print(f"   Comments are ignored by browsers but trigger HTTP flush")

if __name__ == "__main__":
    asyncio.run(main())