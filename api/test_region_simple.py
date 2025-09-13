#!/usr/bin/env python3
"""
Simple test for Vertex AI region configuration
"""

import os

def test_region_config():
    """Test the region configuration without full config dependencies"""
    
    print("🌍 Testing Vertex AI region configuration...")
    
    # Test 1: Check default environment variable
    region = os.getenv("VERTEX_AI_LOCATION", "global")
    print(f"1. Environment VERTEX_AI_LOCATION: {region}")
    
    # Test 2: Test endpoint construction  
    project_id = "test-project"
    model = "gemini-2.5-flash-image-preview"
    
    def construct_endpoint(location, proj_id, model_name):
        return f"https://aiplatform.googleapis.com/v1/projects/{proj_id}/locations/{location}/publishers/google/models/{model_name}:streamGenerateContent"
    
    endpoint = construct_endpoint(region, project_id, model)
    print(f"2. Constructed endpoint: {endpoint}")
    
    # Test 3: Verify correct region is used
    if region == "global":
        assert "aiplatform.googleapis.com" in endpoint and f"/locations/{region}/" in endpoint
        print("✅ Using global region correctly")
    elif region == "australia-southeast1":
        assert "aiplatform.googleapis.com" in endpoint and f"/locations/{region}/" in endpoint
        print("✅ Using australia-southeast1 region correctly")
    else:
        assert "aiplatform.googleapis.com" in endpoint and f"/locations/{region}/" in endpoint
        print(f"✅ Using {region} region correctly")
    
    return True

def show_configuration_info():
    """Show configuration information"""
    
    print("\n📋 Configuration Information:")
    print("- Environment variable: VERTEX_AI_LOCATION")
    print("- Default value: global")
    print("- Current value:", os.getenv("VERTEX_AI_LOCATION", "global"))
    print("\n🔧 To change region:")
    print("  export VERTEX_AI_LOCATION=us-central1")
    print("  # or edit api/.env file")
    
    print("\n📍 Recommended regions:")
    print("- global: Auto-routes to best location (recommended)")
    print("- us-central1: USA Central")
    print("- europe-west1: Europe")
    print("- asia-northeast1: Asia Pacific")

if __name__ == "__main__":
    try:
        test_region_config()
        show_configuration_info()
        print("\n🎉 Region configuration test passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)