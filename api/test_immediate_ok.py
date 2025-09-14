#!/usr/bin/env python3
"""
Test script to verify immediate OK message delivery
Tests the complete pipeline from request to OK message with timing analysis
"""

import asyncio
import time
import json
import sys
from typing import AsyncGenerator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock the dependencies for isolated testing
class MockSettings:
    prompt_analysis_enabled = False
    immediate_response_text = "OK"
    use_simplified_format = True
    add_message_separation = False

class MockFormatter:
    def format_immediate_response(self):
        return 'data: {"candidates": [{"content": {"role": "model", "parts": [{"text": "OK"}]}}]}\n\n'

class MockTranslator:
    def v2_to_vertex(self, request):
        return {"contents": request.contents}
    
    def get_vertex_endpoint(self):
        return "https://mock-vertex-endpoint"

class MockAuthHandler:
    def get_access_token(self):
        return "mock_token"
    
    def get_project_id(self):
        return "mock_project"

class MockV2ChatRequest:
    def __init__(self):
        self.contents = [{"text": "Hello"}]
        self.language = "en"
        self.stream = True

# Mock the global variables
settings = MockSettings()
formatter = MockFormatter()

def get_translator():
    return MockTranslator()

auth_handler = MockAuthHandler()

async def mock_stream_from_vertex_ai(vertex_request, current_translator) -> AsyncGenerator[str, None]:
    """Mock Vertex AI streaming - simulates real response with delay"""
    await asyncio.sleep(0.1)  # Simulate network latency
    yield 'data: {"candidates": [{"content": {"parts": [{"text": "Hello! How can I help you?"}]}}]}\n\n'
    await asyncio.sleep(0.05)
    yield 'data: {"candidates": [{"content": {"parts": [{"text": " I\'m ready to assist."}]}}]}\n\n'

async def stream_v2_enhanced_response_test(request, user: dict) -> AsyncGenerator[str, None]:
    """Test version of the enhanced streaming function with timing"""
    
    start_time = time.time()
    logger.info(f"🚀 Request received at: {start_time}")
    
    try:
        # Step 1: IMMEDIATE "OK" confirmation - send this FIRST before any blocking operations
        logger.info("✅ Sending immediate OK acknowledgment...")
        ok_time = time.time()
        ok_response = formatter.format_immediate_response()
        logger.info(f"⚡ OK generated in: {(ok_time - start_time) * 1000:.2f}ms")
        yield ok_response
        yield_time = time.time()
        logger.info(f"⚡ OK yielded in: {(yield_time - start_time) * 1000:.2f}ms")

        # Step 2: Initialize translator and authentication AFTER OK message
        logger.info("🔧 Initializing translator and authentication...")
        init_start = time.time()
        current_translator = get_translator()
        init_time = time.time()
        logger.info(f"🔧 Initialization took: {(init_time - init_start) * 1000:.2f}ms")
        
        # Step 3: Background analysis (completely skip if disabled)
        if settings.prompt_analysis_enabled:
            logger.info("🧠 Analysis enabled - would run background analysis")
        else:
            logger.info("🔄 Analysis disabled, using pass-through")
        
        # Step 4: Stream from Vertex AI
        logger.info("🎯 Starting mock Vertex AI streaming...")
        vertex_start = time.time()
        vertex_request = current_translator.v2_to_vertex(request)
        
        async for vertex_chunk in mock_stream_from_vertex_ai(vertex_request, current_translator):
            chunk_time = time.time()
            logger.info(f"📦 Vertex chunk at: {(chunk_time - start_time) * 1000:.2f}ms from start")
            yield vertex_chunk
        
        total_time = time.time()
        logger.info(f"✅ Total processing time: {(total_time - start_time) * 1000:.2f}ms")
        
    except Exception as e:
        logger.error(f"❌ Enhanced streaming error: {e}")
        error_message = f"I apologize, but I encountered an error processing your request."
        yield f'data: {{"error": "{error_message}"}}\n\n'

async def test_immediate_response():
    """Test the immediate response timing"""
    logger.info("=" * 60)
    logger.info("🧪 TESTING IMMEDIATE OK MESSAGE DELIVERY")
    logger.info("=" * 60)
    
    request = MockV2ChatRequest()
    user = {"id": "test_user"}
    
    chunks = []
    chunk_times = []
    
    start_time = time.time()
    
    async for chunk in stream_v2_enhanced_response_test(request, user):
        chunk_time = time.time()
        relative_time = (chunk_time - start_time) * 1000  # Convert to ms
        chunks.append(chunk)
        chunk_times.append(relative_time)
        
        logger.info(f"📨 Received chunk #{len(chunks)} at {relative_time:.2f}ms: {chunk[:50]}...")
        
        # Check if this is the OK message
        if 'OK' in chunk and '"text": "OK"' in chunk:
            logger.info(f"🎯 OK MESSAGE DETECTED at {relative_time:.2f}ms")
            break
    
    # Analysis
    logger.info("=" * 60)
    logger.info("📊 TIMING ANALYSIS")
    logger.info("=" * 60)
    
    if chunk_times:
        ok_time = chunk_times[0]
        logger.info(f"✅ OK message delivered in: {ok_time:.2f}ms")
        
        if ok_time < 10:
            logger.info("🚀 EXCELLENT: OK delivered in <10ms")
        elif ok_time < 50:
            logger.info("✅ GOOD: OK delivered in <50ms")
        elif ok_time < 100:
            logger.info("⚠️ ACCEPTABLE: OK delivered in <100ms")
        else:
            logger.info("❌ SLOW: OK delivered in >100ms - needs optimization")
    
    logger.info(f"📦 Total chunks received: {len(chunks)}")
    logger.info("=" * 60)
    
    return chunk_times[0] if chunk_times else float('inf')

async def test_multiple_requests():
    """Test multiple requests to verify consistency"""
    logger.info("🔄 Testing consistency across multiple requests...")
    
    times = []
    for i in range(5):
        logger.info(f"\n--- Request {i+1}/5 ---")
        ok_time = await test_immediate_response()
        times.append(ok_time)
        await asyncio.sleep(0.1)  # Small delay between tests
    
    logger.info("=" * 60)
    logger.info("📈 CONSISTENCY ANALYSIS")
    logger.info("=" * 60)
    logger.info(f"Average OK time: {sum(times)/len(times):.2f}ms")
    logger.info(f"Min OK time: {min(times):.2f}ms")
    logger.info(f"Max OK time: {max(times):.2f}ms")
    logger.info(f"Time variation: {max(times) - min(times):.2f}ms")
    
    consistent = all(t < 50 for t in times)
    logger.info(f"All responses <50ms: {'✅ YES' if consistent else '❌ NO'}")

def test_sse_format():
    """Test the exact SSE format of OK message"""
    logger.info("=" * 60)
    logger.info("🔍 TESTING SSE FORMAT")
    logger.info("=" * 60)
    
    ok_response = formatter.format_immediate_response()
    logger.info(f"Raw OK response: {repr(ok_response)}")
    
    # Check SSE format
    if ok_response.startswith('data: '):
        logger.info("✅ Starts with 'data: '")
    else:
        logger.error("❌ Missing 'data: ' prefix")
    
    if ok_response.endswith('\n\n'):
        logger.info("✅ Ends with '\\n\\n'")
    else:
        logger.error("❌ Missing '\\n\\n' terminator")
    
    # Parse JSON content
    try:
        json_part = ok_response[5:-2]  # Remove 'data: ' and '\n\n'
        data = json.loads(json_part)
        logger.info(f"✅ Valid JSON: {data}")
        
        # Check Vertex AI format
        if 'candidates' in data and isinstance(data['candidates'], list):
            logger.info("✅ Has candidates array")
            if data['candidates'] and 'content' in data['candidates'][0]:
                content = data['candidates'][0]['content']
                if 'parts' in content and content['parts']:
                    text = content['parts'][0].get('text')
                    if text == 'OK':
                        logger.info("✅ Contains exact 'OK' text")
                    else:
                        logger.error(f"❌ Text is '{text}', not 'OK'")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON: {e}")

if __name__ == "__main__":
    print("🧪 WonderCam Immediate OK Message Test")
    print("This test verifies the OK message is sent immediately without blocking operations")
    print()
    
    # Run format test first
    test_sse_format()
    
    # Run timing tests
    asyncio.run(test_immediate_response())
    print()
    
    # Run consistency test
    if len(sys.argv) > 1 and sys.argv[1] == "--consistency":
        asyncio.run(test_multiple_requests())
    else:
        print("💡 Run with --consistency flag to test multiple requests")