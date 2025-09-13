#!/usr/bin/env python3
"""
Test V2 API fixes for user object access and user-only content processing
"""

import json
import asyncio
from v2_models import V2ChatRequest, V2ContentPart
from v2_translator import V2MessageTranslator

async def test_v2_user_content_processing():
    """Test V2 API user content validation and processing"""
    
    print("🧪 Testing V2 API user content processing...")
    
    # Test case 1: Valid multimodal user content
    print("1. Testing valid multimodal content...")
    valid_request = V2ChatRequest(
        contents=[
            V2ContentPart(text="Respond in English. Analyze this image"),
            V2ContentPart(inlineData={
                "mimeType": "image/jpeg",
                "data": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAoHBwgHBgoICAgL"
            })
        ],
        language="en",
        stream=True
    )
    
    translator = V2MessageTranslator(project_id="test-project")
    
    try:
        # Test validation
        validation = translator.validate_user_content(valid_request)
        print(f"   ✅ Validation: {validation['summary']}")
        assert validation["valid"], f"Validation failed: {validation['issues']}"
        
        # Test conversion to Vertex AI
        vertex_request = translator.v2_to_vertex(valid_request)
        vertex_data = vertex_request.model_dump()
        
        print(f"   ✅ Vertex conversion: {len(vertex_data['contents'])} contents")
        assert len(vertex_data['contents']) == 1, "Should create single user content"
        assert vertex_data['contents'][0]['role'] == 'user', "Content should be user role"
        
        parts = vertex_data['contents'][0]['parts']
        text_parts = [p for p in parts if 'text' in p]
        image_parts = [p for p in parts if 'inlineData' in p]
        
        print(f"   📝 Parts: {len(text_parts)} text, {len(image_parts)} image")
        assert len(text_parts) >= 1, "Should have at least 1 text part (instruction + user text)"
        assert len(image_parts) == 1, "Should have 1 image part"
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test case 2: Content with validation issues
    print("2. Testing content with validation issues...")
    problematic_request = V2ChatRequest(
        contents=[
            V2ContentPart(text="   "),  # Empty text after strip
            V2ContentPart(inlineData={"mimeType": "unknown/type", "data": "somedata"}),  # Unknown mime type
            V2ContentPart()  # Neither text nor inlineData
        ],
        language="zh",
        stream=True
    )
    
    try:
        validation = translator.validate_user_content(problematic_request)
        print(f"   ✅ Validation caught issues: {len(validation['issues'])} issues")
        assert not validation["valid"], "Should detect validation issues"
        assert len(validation["issues"]) >= 2, "Should detect multiple issues"
        
        # Should still process despite issues
        vertex_request = translator.v2_to_vertex(problematic_request)
        vertex_data = vertex_request.model_dump()
        
        print(f"   ✅ Processed despite issues: {len(vertex_data['contents'])} contents")
        parts = vertex_data['contents'][0]['parts']
        print(f"   📝 Final parts count: {len(parts)}")
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test case 3: Audio content
    print("3. Testing audio content support...")
    audio_request = V2ChatRequest(
        contents=[
            V2ContentPart(text="Transcribe this audio"),
            V2ContentPart(inlineData={
                "mimeType": "audio/webm",
                "data": "UklGRnoAAABXQVZFZm10IBAAAAABAAEA="
            })
        ],
        language="ja",
        stream=True
    )
    
    try:
        validation = translator.validate_user_content(audio_request)
        print(f"   ✅ Audio validation: {validation['summary']}")
        assert validation["summary"]["audio_parts"] == 1, "Should detect audio content"
        
        vertex_request = translator.v2_to_vertex(audio_request)
        vertex_data = vertex_request.model_dump()
        
        parts = vertex_data['contents'][0]['parts']
        audio_parts = [p for p in parts if p.get('inlineData', {}).get('mimeType', '').startswith('audio/')]
        print(f"   🎵 Audio parts in Vertex request: {len(audio_parts)}")
        assert len(audio_parts) == 1, "Should preserve audio content"
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    print("\n🎉 All V2 user content processing tests passed!")
    return True

async def test_v2_preprocessing():
    """Test V2 preprocessing with user content"""
    
    print("\n🔧 Testing V2 preprocessing...")
    
    # Test image analysis preprocessing
    image_request = V2ChatRequest(
        contents=[
            V2ContentPart(text="Please analyze this medical image"),
            V2ContentPart(inlineData={
                "mimeType": "image/png",
                "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
            })
        ],
        language="en"
    )
    
    translator = V2MessageTranslator(project_id="test-project")
    
    try:
        preprocess_chunks = []
        async for chunk in translator.preprocess_request(image_request):
            preprocess_chunks.append(chunk)
        
        print(f"   ✅ Generated {len(preprocess_chunks)} preprocessing messages")
        
        # Should detect image analysis intent
        system_chunks = [c for c in preprocess_chunks if c.type == "system"]
        if system_chunks:
            print(f"   📋 System message: {system_chunks[0].content}")
        
        # Test intent detection
        intents = translator.detect_content_intent(image_request)
        print(f"   🎯 Detected intents: {intents}")
        assert intents["image_analysis"], "Should detect image analysis intent"
        assert not intents["general_chat"], "Should not be general chat"
        
    except Exception as e:
        print(f"   ❌ Preprocessing failed: {e}")
        return False
    
    print("   ✅ V2 preprocessing tests passed!")
    return True

def test_vertex_request_structure():
    """Test the structure of generated Vertex AI requests"""
    
    print("\n📄 Testing Vertex AI request structure...")
    
    # Complex multimodal request
    complex_request = V2ChatRequest(
        contents=[
            V2ContentPart(text="Here are my questions:"),
            V2ContentPart(text="1. What's in this image?"),
            V2ContentPart(inlineData={
                "mimeType": "image/jpeg",
                "data": "base64imagedata1"
            }),
            V2ContentPart(text="2. What's in this other image?"),
            V2ContentPart(inlineData={
                "mimeType": "image/png", 
                "data": "base64imagedata2"
            }),
            V2ContentPart(text="Please provide detailed analysis.")
        ],
        language="fr"
    )
    
    translator = V2MessageTranslator(project_id="test-project")
    
    try:
        vertex_request = translator.v2_to_vertex(complex_request)
        vertex_data = vertex_request.model_dump()
        
        print(f"   ✅ Request structure validated")
        print(f"      - Contents: {len(vertex_data['contents'])}")
        print(f"      - Role: {vertex_data['contents'][0]['role']}")
        
        parts = vertex_data['contents'][0]['parts']
        text_parts = [p for p in parts if 'text' in p]
        image_parts = [p for p in parts if 'inlineData' in p]
        
        print(f"      - Text parts: {len(text_parts)} (includes language instruction)")
        print(f"      - Image parts: {len(image_parts)}")
        print(f"      - Total parts: {len(parts)}")
        
        # Check language instruction was added
        first_text = text_parts[0]['text'] if text_parts else ""
        assert "français" in first_text.lower(), "Should include French language instruction"
        
        # Check all images preserved
        assert len(image_parts) == 2, "Should preserve both images"
        
        # Check generation config
        gen_config = vertex_data['generationConfig']
        print(f"      - Response modalities: {gen_config.get('responseModalities', [])}")
        assert "TEXT" in gen_config.get('responseModalities', []), "Should support text response"
        assert "IMAGE" in gen_config.get('responseModalities', []), "Should support image response"
        
        print("   ✅ Vertex AI request structure is correct!")
        return True
        
    except Exception as e:
        print(f"   ❌ Structure test failed: {e}")
        return False

async def main():
    """Run all V2 API fix tests"""
    print("🚀 Starting V2 API fix validation...\n")
    
    test1 = await test_v2_user_content_processing()
    test2 = await test_v2_preprocessing() 
    test3 = test_vertex_request_structure()
    
    all_passed = test1 and test2 and test3
    
    if all_passed:
        print("\n✅ All V2 API fixes validated! Ready for production.")
        print("📋 Summary:")
        print("   - User object access fixed")
        print("   - User-only content processing implemented")
        print("   - Content validation and error handling added")
        print("   - Proper Vertex AI conversation structure created")
        print("   - Multimodal support (text, image, audio) working")
        print("   - Language instructions and preprocessing functional")
    else:
        print("\n❌ Some V2 API fix tests failed. Please review the errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)