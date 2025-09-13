#!/usr/bin/env python3
"""
Test V2 API simplified Gemini-compatible request format
"""

import json
from v2_models import V2ChatRequest, V2ContentPart

def test_v2_simplified_format():
    """Test the new simplified V2 request format"""
    
    print("🧪 Testing V2 API simplified format...")
    
    # Test 1: Text only request
    print("1. Testing text-only request...")
    text_request = {
        "contents": [
            {"text": "Respond in English. Hello, how are you?"}
        ],
        "language": "en",
        "stream": True
    }
    
    try:
        request = V2ChatRequest(**text_request)
        print(f"✅ Text request validation passed: {len(request.contents)} parts")
        print(f"   First part: {request.contents[0].text[:50]}...")
    except Exception as e:
        print(f"❌ Text request failed: {e}")
        return False
    
    # Test 2: Text + Image request (Gemini-compatible format)
    print("2. Testing text + image request...")
    multimodal_request = {
        "contents": [
            {"text": "Respond in English. Analyze this image"},
            {
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8lJCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+JS5ESUM8SDc9Pjv/2wBDAQoLCw4NDhwQEBw7KCIoOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozv/wAARCAMABAADASIAAhEBAxEB"
                }
            }
        ],
        "language": "en",
        "stream": True
    }
    
    try:
        request = V2ChatRequest(**multimodal_request)
        print(f"✅ Multimodal request validation passed: {len(request.contents)} parts")
        
        text_parts = [p for p in request.contents if p.text]
        image_parts = [p for p in request.contents if p.inlineData]
        print(f"   Text parts: {len(text_parts)}, Image parts: {len(image_parts)}")
        
    except Exception as e:
        print(f"❌ Multimodal request failed: {e}")
        return False
    
    # Test 3: Voice content (future)
    print("3. Testing voice content...")
    voice_request = {
        "contents": [
            {"text": "Transcribe this audio"},
            {
                "inlineData": {
                    "mimeType": "audio/webm",
                    "data": "UklGRnoAAABXQVZFZm10IBAAAAABAAEA=="
                }
            }
        ],
        "language": "en",
        "stream": True
    }
    
    try:
        request = V2ChatRequest(**voice_request)
        print(f"✅ Voice request validation passed: {len(request.contents)} parts")
        
        audio_parts = [p for p in request.contents if p.inlineData and p.inlineData.get("mimeType", "").startswith("audio/")]
        print(f"   Audio parts: {len(audio_parts)}")
        
    except Exception as e:
        print(f"❌ Voice request failed: {e}")
        return False
    
    # Test 4: JSON serialization
    print("4. Testing JSON serialization...")
    try:
        json_data = json.dumps(request.model_dump(), indent=2)
        print(f"✅ JSON serialization works: {len(json_data)} chars")
        print("Sample JSON structure:")
        print(json.dumps(request.model_dump(), indent=2)[:200] + "...")
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False
    
    print("\n🎉 All V2 simplified format tests passed!")
    return True

def test_flexible_content_part():
    """Test V2ContentPart flexibility"""
    
    print("\n🔧 Testing V2ContentPart flexibility...")
    
    # Test text part
    text_part = V2ContentPart(text="Hello world")
    print(f"✅ Text part: {text_part}")
    
    # Test inline data part
    image_part = V2ContentPart(inlineData={"mimeType": "image/jpeg", "data": "base64data"})
    print(f"✅ Image part: {image_part}")
    
    # Test empty part (should be valid but not useful)
    try:
        empty_part = V2ContentPart()
        print(f"✅ Empty part allowed: {empty_part}")
    except Exception as e:
        print(f"ℹ️  Empty part validation: {e}")
    
    print("✅ V2ContentPart flexibility tests complete!")

if __name__ == "__main__":
    success = test_v2_simplified_format()
    test_flexible_content_part()
    exit(0 if success else 1)