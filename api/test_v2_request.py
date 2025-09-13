#!/usr/bin/env python3
"""
Test V2 API request format validation
"""

import json
from v2_models import V2ChatRequest, V2Message, V2MessageContentSimple

def test_v2_request_validation():
    """Test if V2 request format matches what frontend sends"""
    
    print("🧪 Testing V2 API request validation...")
    
    # Simulate what frontend sends
    frontend_request = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "data": "Hello, world!"
                    }
                ],
                "timestamp": "2025-09-13T12:00:00.000Z",
                "message_id": "test-123"
            }
        ],
        "language": "en",
        "session_id": "test-session",
        "stream": True
    }
    
    try:
        # Test Pydantic validation
        print("1. Testing V2MessageContentSimple validation...")
        content = V2MessageContentSimple(**frontend_request["messages"][0]["content"][0])
        print(f"✅ Content validation passed: {content}")
        
        print("2. Testing V2Message validation...")
        message = V2Message(**frontend_request["messages"][0])
        print(f"✅ Message validation passed: {message}")
        
        print("3. Testing V2ChatRequest validation...")
        request = V2ChatRequest(**frontend_request)
        print(f"✅ Request validation passed: {request}")
        
        print("4. Testing JSON serialization...")
        json_data = json.dumps(request.model_dump(), indent=2)
        print(f"✅ JSON serialization works: {len(json_data)} chars")
        
        print("\n🎉 All V2 API validation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ V2 API validation failed: {e}")
        print(f"Frontend request: {json.dumps(frontend_request, indent=2)}")
        return False

if __name__ == "__main__":
    success = test_v2_request_validation()
    exit(0 if success else 1)