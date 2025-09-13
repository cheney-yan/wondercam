#!/usr/bin/env python3
"""
Final V2 API endpoint validation test
"""

import os
from v2_translator import V2MessageTranslator

def test_v2_final_endpoint():
    """Test the final V2 endpoint configuration"""
    
    print("🏁 Final V2 API Endpoint Validation...")
    
    # Create translator with test project
    translator = V2MessageTranslator(project_id="awesome-tensor-471623-a7")
    
    # Test 1: Default endpoint (global)
    endpoint = translator.get_vertex_endpoint()
    print(f"1. Default endpoint: {endpoint}")
    
    expected_parts = [
        "https://aiplatform.googleapis.com/v1/projects/awesome-tensor-471623-a7",
        "/locations/global/",
        "publishers/google/models/gemini-2.5-flash-image-preview",
        ":streamGenerateContent"
    ]
    
    for part in expected_parts:
        assert part in endpoint, f"Missing expected part: {part}"
    
    print("   ✅ All expected URL components present")
    
    # Test 2: Verify it uses streamGenerateContent (not regular generateContent)
    assert ":streamGenerateContent" in endpoint, "Should use streamGenerateContent endpoint"
    assert ":generateContent" not in endpoint or ":streamGenerateContent" in endpoint, "Should use streaming version"
    print("   ✅ Correctly uses streamGenerateContent endpoint")
    
    # Test 3: Verify region configuration
    region = os.getenv("VERTEX_AI_LOCATION", "global")
    assert f"/locations/{region}/" in endpoint, f"Should use configured region: {region}"
    print(f"   ✅ Using configured region: {region}")
    
    # Test 4: Test with different model
    custom_endpoint = translator.get_vertex_endpoint("gemini-2.5-pro")
    assert "gemini-2.5-pro" in custom_endpoint, "Should support custom models"
    print("   ✅ Supports custom model names")
    
    print("\n📋 Final V2 Endpoint Configuration:")
    print(f"   Base: https://aiplatform.googleapis.com/v1/")
    print(f"   Project: awesome-tensor-471623-a7")
    print(f"   Region: {region} (from VERTEX_AI_LOCATION env var)")
    print(f"   Model: gemini-2.5-flash-image-preview (default)")
    print(f"   Action: streamGenerateContent")
    print(f"   Full: {endpoint}")
    
    return True

def compare_v1_v2_endpoints():
    """Compare V1beta and V2 endpoints"""
    
    print("\n🔄 V1beta vs V2 Endpoint Comparison:")
    
    project_id = "awesome-tensor-471623-a7"
    region = "global"
    model = "gemini-2.5-flash-image-preview"
    
    # V1beta endpoint (from endpoint_translator.py) - non-streaming
    v1beta_endpoint = f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/publishers/google/models/{model}:generateContent"
    
    # V2 endpoint (from v2_translator.py) 
    translator = V2MessageTranslator(project_id=project_id)
    v2_endpoint = translator.get_vertex_endpoint(model)
    
    print(f"V1beta: {v1beta_endpoint}")
    print(f"V2:     {v2_endpoint}")
    
    # They should be different - V1beta uses generateContent, V2 uses streamGenerateContent
    assert v1beta_endpoint != v2_endpoint, "V1beta and V2 should use different endpoints"
    assert ":generateContent" in v1beta_endpoint, "V1beta should use generateContent"
    assert ":streamGenerateContent" in v2_endpoint, "V2 should use streamGenerateContent"
    print("✅ V1beta and V2 correctly use different endpoints (streaming vs non-streaming)")
    
    print("\n📊 Key Differences:")
    print("- Frontend paths: /v1beta/models/* vs /v2/chat")
    print("- Request format: Gemini-compatible vs Simplified")
    print("- Authentication: x-goog-api-key+Bearer vs Bearer-only")
    print("- Response processing: Direct proxy vs Stream interception")
    print("- Backend endpoint: V1beta=generateContent, V2=streamGenerateContent ✅")

if __name__ == "__main__":
    try:
        test_v2_final_endpoint()
        compare_v1_v2_endpoints()
        print("\n🎉 All V2 endpoint validation tests passed!")
        print("V2 API is correctly configured and ready for production!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)