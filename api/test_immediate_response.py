#!/usr/bin/env python3
"""
Test script for immediate response functionality
Tests the optimized streaming response to ensure OK message is sent immediately
"""

import asyncio
import json
import time
from fastapi.testclient import TestClient
from v2_models import V2ChatRequest, V2ContentPart
from main import app

async def test_immediate_response():
    """Test that OK message is sent immediately"""
    
    print("🧪 Testing immediate response functionality...")
    
    # Create test request
    request = V2ChatRequest(
        contents=[
            V2ContentPart(text="Hello, can you help me with something?")
        ],
        language="en",
        stream=True
    )
    
    # Mock user for auth
    mock_user = type('MockUser', (), {'id': 'test_user'})()
    
    # Import the streaming function
    from v2_api_enhanced import stream_v2_enhanced_response
    
    print("📡 Starting streaming response test...")
    start_time = time.time()
    
    first_chunk_time = None
    chunks_received = []
    
    async for chunk in stream_v2_enhanced_response(request, mock_user):
        current_time = time.time()
        elapsed = current_time - start_time
        
        if first_chunk_time is None:
            first_chunk_time = elapsed
            print(f"⚡ First chunk received in {first_chunk_time:.3f}s")
        
        chunks_received.append({
            'time': elapsed,
            'chunk': chunk[:100] + "..." if len(chunk) > 100 else chunk
        })
        
        print(f"📦 Chunk {len(chunks_received)} at {elapsed:.3f}s: {chunk[:50]}...")
        
        # Stop after first few chunks for testing
        if len(chunks_received) >= 3:
            break
    
    print(f"\n📊 Test Results:")
    print(f"   Total chunks received: {len(chunks_received)}")
    print(f"   First chunk time: {first_chunk_time:.3f}s")
    print(f"   Expected: < 0.1s for immediate response")
    
    # Check if first chunk contains OK message
    if chunks_received:
        first_chunk = chunks_received[0]['chunk']
        try:
            # Parse SSE format
            if first_chunk.startswith("data: "):
                json_data = first_chunk[6:].strip()
                data = json.loads(json_data)
                text_content = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                
                if "OK" in text_content:
                    print(f"✅ OK message found in first chunk: '{text_content.strip()}'")
                else:
                    print(f"❌ OK message NOT found. Content: '{text_content}'")
            else:
                print(f"❌ First chunk not in SSE format: {first_chunk}")
                
        except Exception as e:
            print(f"❌ Error parsing first chunk: {e}")
    
    return first_chunk_time

async def test_config_settings():
    """Test configuration settings"""
    
    print("\n🔧 Testing configuration settings...")
    
    from config import settings
    
    print(f"   immediate_response_text: '{settings.immediate_response_text}'")
    print(f"   prompt_analysis_enabled: {settings.prompt_analysis_enabled}")
    print(f"   prompt_analysis_timeout: {settings.prompt_analysis_timeout}s")
    print(f"   add_message_separation: {settings.add_message_separation}")
    
    return settings

async def test_vertex_formatter():
    """Test vertex formatter for immediate response"""
    
    print("\n🎨 Testing vertex formatter...")
    
    from vertex_formatter import VertexAIResponseFormatter
    
    start_time = time.time()
    formatted_response = VertexAIResponseFormatter.format_immediate_response()
    format_time = time.time() - start_time
    
    print(f"   Format time: {format_time:.6f}s")
    print(f"   Formatted response: {formatted_response}")
    
    # Parse the response
    try:
        if formatted_response.startswith("data: "):
            json_data = formatted_response[6:].strip()
            data = json.loads(json_data)
            text_content = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            print(f"✅ Parsed text content: '{text_content}'")
        else:
            print(f"❌ Not in SSE format")
    except Exception as e:
        print(f"❌ Parse error: {e}")
    
    return format_time

async def main():
    """Run all tests"""
    
    print("🚀 Starting immediate response tests...\n")
    
    # Test configuration
    settings = await test_config_settings()
    
    # Test formatter performance
    format_time = await test_vertex_formatter()
    
    # Test full streaming response
    response_time = await test_immediate_response()
    
    print(f"\n📋 Summary:")
    print(f"   Formatter performance: {format_time:.6f}s")
    print(f"   First chunk delivery: {response_time:.3f}s")
    
    if response_time < 0.1:
        print("✅ PASS: Immediate response is fast enough")
    elif response_time < 0.5:
        print("⚠️  CAUTION: Response is acceptable but could be faster")
    else:
        print("❌ FAIL: Response is too slow for 'immediate' feedback")

if __name__ == "__main__":
    asyncio.run(main())