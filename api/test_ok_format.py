#!/usr/bin/env python3
"""
Test the exact format of the OK message to ensure it's just "OK" and not "OK\n\n"
"""

from vertex_formatter import VertexAIResponseFormatter
from config import settings
import json

def test_ok_format():
    """Test that OK message format is exactly correct"""
    
    print("🧪 Testing OK message format...")
    
    # Get the formatted immediate response
    formatted_response = VertexAIResponseFormatter.format_immediate_response()
    
    print(f"📤 Full formatted response:")
    print(repr(formatted_response))
    
    # Parse the SSE data
    if formatted_response.startswith("data: "):
        json_part = formatted_response[6:].strip()
        try:
            parsed = json.loads(json_part)
            text_content = parsed["candidates"][0]["content"]["parts"][0]["text"]
            
            print(f"\n📝 Extracted text content: {repr(text_content)}")
            print(f"   Length: {len(text_content)} characters")
            
            if text_content == "OK":
                print("✅ PASS: Text content is exactly 'OK'")
            else:
                print(f"❌ FAIL: Text content is '{text_content}', expected 'OK'")
            
            # Check for extra newlines
            if "\n" in text_content:
                print(f"⚠️  WARNING: Text contains newlines: {repr(text_content)}")
            else:
                print("✅ PASS: No extra newlines in text content")
                
        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
    else:
        print(f"❌ Response doesn't start with 'data: '")
    
    # Test configuration
    print(f"\n🔧 Configuration:")
    print(f"   immediate_response_text: {repr(settings.immediate_response_text)}")
    print(f"   add_message_separation: {settings.add_message_separation}")

if __name__ == "__main__":
    test_ok_format()