#!/usr/bin/env python3
"""
Test Vertex AI region configuration
"""

import os
from config import settings
from v2_translator import V2MessageTranslator

def test_region_configuration():
    """Test that the region configuration works correctly"""
    
    print("🌍 Testing Vertex AI region configuration...")
    
    # Test 1: Default configuration (should be 'global')
    print(f"1. Default region setting: {settings.vertex_ai_location}")
    assert settings.vertex_ai_location == "global", f"Expected 'global', got '{settings.vertex_ai_location}'"
    
    # Test 2: Create translator and check endpoint
    translator = V2MessageTranslator(project_id="test-project")
    endpoint = translator.get_vertex_endpoint()
    
    print(f"2. Generated endpoint: {endpoint}")
    assert "aiplatform.googleapis.com" in endpoint and "/locations/global/" in endpoint, f"Endpoint should use global region: {endpoint}"
    
    # Test 3: Test with different environment variable
    original_location = settings.vertex_ai_location
    
    # Temporarily change the environment variable
    os.environ["VERTEX_AI_LOCATION"] = "us-central1"
    
    # Recreate settings to pick up new env var
    from config import Settings
    test_settings = Settings()
    
    print(f"3. Modified region setting: {test_settings.vertex_ai_location}")
    assert test_settings.vertex_ai_location == "us-central1", f"Expected 'us-central1', got '{test_settings.vertex_ai_location}'"
    
    # Test endpoint with new region
    translator_custom = V2MessageTranslator(project_id="test-project")
    # Temporarily override settings for this test
    import v2_translator
    original_settings = v2_translator.settings
    v2_translator.settings = test_settings
    
    endpoint_custom = translator_custom.get_vertex_endpoint()
    print(f"4. Custom region endpoint: {endpoint_custom}")
    assert "aiplatform.googleapis.com" in endpoint_custom and "/locations/us-central1/" in endpoint_custom, f"Endpoint should use us-central1: {endpoint_custom}"
    
    # Restore original settings
    v2_translator.settings = original_settings
    os.environ["VERTEX_AI_LOCATION"] = original_location
    
    print("✅ All region configuration tests passed!")
    
    return True

def show_available_regions():
    """Show information about available Vertex AI regions"""
    
    print("\n📍 Vertex AI Regions Information:")
    print("Available regions for Vertex AI:")
    print("- global: Default region, automatically routes to best location")
    print("- us-central1: Iowa, USA")
    print("- us-east1: South Carolina, USA")
    print("- us-west1: Oregon, USA") 
    print("- europe-west1: Belgium, Europe")
    print("- europe-west4: Netherlands, Europe")
    print("- asia-east1: Taiwan, Asia")
    print("- asia-northeast1: Tokyo, Japan")
    print("- asia-southeast1: Singapore, Asia")
    print("- australia-southeast1: Sydney, Australia")
    
    print(f"\n🔧 Current configuration: {settings.vertex_ai_location}")
    print("💡 Change via environment variable: VERTEX_AI_LOCATION=us-central1")

if __name__ == "__main__":
    try:
        test_region_configuration()
        show_available_regions()
        print("\n🎉 Region configuration is working correctly!")
    except Exception as e:
        print(f"❌ Region configuration test failed: {e}")
        exit(1)