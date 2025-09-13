#!/usr/bin/env python3
"""
Test script to check if V2 API imports work correctly
"""

import sys
import traceback

def test_imports():
    """Test all V2 API imports"""
    
    print("🔍 Testing V2 API imports...")
    
    try:
        print("1. Testing v2_models import...")
        from v2_models import V2ChatRequest, V2ResponseChunk, V2Message, MessageType
        print("✅ v2_models imported successfully")
        
        print("2. Testing v2_translator import...")
        from v2_translator import V2MessageTranslator
        print("✅ v2_translator imported successfully")
        
        print("3. Testing v2_api import...")
        from v2_api import v2_router
        print("✅ v2_api imported successfully")
        
        print("4. Testing main import with v2_router...")
        from main import app
        print("✅ main imported successfully")
        
        # Test creating a simple V2 message
        print("5. Testing V2 message creation...")
        test_message = V2Message(
            role="user",
            content=[{"type": "text", "data": "Hello"}]
        )
        print(f"✅ V2 message created: {test_message}")
        
        print("✅ All V2 API imports and basic functionality working!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_v2_endpoints():
    """Test if V2 endpoints are accessible"""
    
    print("\n🌐 Testing V2 API endpoints...")
    
    try:
        import httpx
        import asyncio
        
        async def test_health():
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get("http://localhost:8000/v2/health")
                    print(f"✅ V2 health endpoint accessible: {response.status_code}")
                    if response.status_code == 200:
                        print(f"Response: {response.json()}")
                    return response.status_code == 200
                except Exception as e:
                    print(f"❌ V2 health endpoint failed: {e}")
                    return False
        
        return asyncio.run(test_health())
        
    except ImportError:
        print("⚠️ httpx not available, skipping endpoint test")
        return True
    except Exception as e:
        print(f"❌ Endpoint test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 WonderCam V2 API Test Suite")
    print("=" * 40)
    
    import_success = test_imports()
    endpoint_success = test_v2_endpoints()
    
    print("\n📊 Test Results:")
    print(f"Imports: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"Endpoints: {'✅ PASS' if endpoint_success else '❌ FAIL'}")
    
    if import_success and endpoint_success:
        print("\n🎉 V2 API is ready!")
        sys.exit(0)
    else:
        print("\n💥 V2 API has issues that need fixing")
        sys.exit(1)