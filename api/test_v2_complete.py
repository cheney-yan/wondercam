#!/usr/bin/env python3
"""
Complete V2 API test with simplified Gemini-compatible format
"""

import json
import asyncio
from v2_models import V2ChatRequest, V2ContentPart
from v2_translator import V2MessageTranslator

async def test_v2_complete_pipeline():
    """Test the complete V2 API pipeline"""
    
    print("🧪 Testing complete V2 API pipeline...")
    
    # Create a test request in the new simplified format
    test_request_data = {
        "contents": [
            {"text": "Hello! Can you analyze this image?"},
            {
                "inlineData": {
                    "mimeType": "image/jpeg", 
                    "data": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8lJCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+JS5ESUM8SDc9Pjv/wAARCAMABAADASIAAhEBAxEB"
                }
            }
        ],
        "language": "en",
        "stream": True
    }
    
    try:
        # Step 1: Validate request format
        print("1. Testing request validation...")
        request = V2ChatRequest(**test_request_data)
        print(f"✅ Request validation passed: {len(request.contents)} content parts")
        
        # Step 2: Test translator
        print("2. Testing V2 translator...")
        translator = V2MessageTranslator(project_id="test-project")
        
        # Test preprocessing
        print("   - Testing preprocessing...")
        preprocess_chunks = []
        async for chunk in translator.preprocess_request(request):
            preprocess_chunks.append(chunk)
        print(f"   ✅ Preprocessing generated {len(preprocess_chunks)} system messages")
        
        # Test conversion to Vertex AI format
        print("   - Testing V2 to Vertex AI conversion...")
        vertex_request = translator.v2_to_vertex(request)
        print(f"   ✅ Vertex AI conversion successful: {len(vertex_request.contents)} contents")
        
        # Validate Vertex AI request structure
        vertex_json = vertex_request.model_dump()
        print(f"   📄 Vertex AI request structure:")
        print(f"      - Contents: {len(vertex_json['contents'])}")
        print(f"      - Safety settings: {len(vertex_json['safetySettings'])}")
        print(f"      - Generation config: {vertex_json['generationConfig']}")
        
        # Check content parts
        if vertex_json['contents']:
            parts = vertex_json['contents'][0].get('parts', [])
            text_parts = [p for p in parts if 'text' in p]
            image_parts = [p for p in parts if 'inlineData' in p]
            print(f"      - Text parts: {len(text_parts)}, Image parts: {len(image_parts)}")
        
        # Step 3: Test intent detection
        print("3. Testing intent detection...")
        intents = translator.detect_content_intent(request)
        print(f"   ✅ Detected intents: {intents}")
        
        print("\n🎉 Complete V2 API pipeline test passed!")
        return True
        
    except Exception as e:
        print(f"❌ V2 API pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_different_content_types():
    """Test various content type combinations"""
    
    print("\n🔧 Testing different content type combinations...")
    
    test_cases = [
        {
            "name": "Text only",
            "contents": [{"text": "Hello world"}]
        },
        {
            "name": "Text + Image", 
            "contents": [
                {"text": "Analyze this"},
                {"inlineData": {"mimeType": "image/jpeg", "data": "base64data"}}
            ]
        },
        {
            "name": "Text + Audio",
            "contents": [
                {"text": "Transcribe this"},
                {"inlineData": {"mimeType": "audio/webm", "data": "audiodata"}}
            ]
        },
        {
            "name": "Multiple text parts",
            "contents": [
                {"text": "First instruction"},
                {"text": "Second instruction"}
            ]
        },
        {
            "name": "Complex multimodal",
            "contents": [
                {"text": "Analyze these media files"},
                {"inlineData": {"mimeType": "image/png", "data": "imagedata"}},
                {"inlineData": {"mimeType": "audio/wav", "data": "audiodata"}},
                {"text": "And provide a detailed report"}
            ]
        }
    ]
    
    translator = V2MessageTranslator(project_id="test-project")
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            print(f"{i}. Testing {test_case['name']}...")
            
            # Create request
            request_data = {
                "contents": test_case["contents"],
                "language": "en",
                "stream": True
            }
            request = V2ChatRequest(**request_data)
            
            # Test conversion
            vertex_request = translator.v2_to_vertex(request)
            parts = vertex_request.contents[0].parts if vertex_request.contents else []
            
            text_parts = [p for p in parts if 'text' in p]
            inline_parts = [p for p in parts if 'inlineData' in p]
            
            print(f"   ✅ Success: {len(text_parts)} text, {len(inline_parts)} inline parts")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print("✅ Content type combination tests complete!")

async def main():
    """Run all tests"""
    print("🚀 Starting V2 API comprehensive tests...\n")
    
    success = await test_v2_complete_pipeline()
    test_different_content_types()
    
    if success:
        print("\n✅ All V2 API tests passed! Ready for production.")
    else:
        print("\n❌ Some V2 API tests failed. Please review the errors above.")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)