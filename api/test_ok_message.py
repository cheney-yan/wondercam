#!/usr/bin/env python3
"""
Test script to verify the OK message format and SSE structure
"""

import json
import sys
import os

# Add the current directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vertex_formatter import VertexAIResponseFormatter
from config import settings

def test_ok_message_format():
    print("🧪 Testing OK message format...")
    print(f"📋 Settings: immediate_response_text = '{settings.immediate_response_text}'")
    print(f"📋 Settings: add_message_separation = {settings.add_message_separation}")
    
    # Test the immediate response format
    immediate_response = VertexAIResponseFormatter.format_immediate_response()
    print(f"\n📤 Formatted immediate response:")
    print(repr(immediate_response))
    
    # Test the text chunk format directly
    text_chunk = VertexAIResponseFormatter.format_text_chunk("OK", is_final=False, add_newlines=False)
    print(f"\n📤 Direct text chunk format:")
    print(repr(text_chunk))
    
    # Parse the JSON to verify structure
    try:
        lines = immediate_response.strip().split('\n')
        for line in lines:
            if line.startswith('data:'):
                json_str = line[5:].strip()
                if json_str:
                    data = json.loads(json_str)
                    print(f"\n✅ Parsed JSON structure:")
                    print(f"   - Has candidates: {'candidates' in data}")
                    print(f"   - Has content: {'content' in data.get('candidates', [{}])[0] if data.get('candidates') else False}")
                    print(f"   - Has parts: {'parts' in data.get('candidates', [{}])[0].get('content', {}) if data.get('candidates') else False}")
                    if data.get('candidates') and data['candidates'][0].get('content', {}).get('parts'):
                        part = data['candidates'][0]['content']['parts'][0]
                        print(f"   - Text content: '{part.get('text', 'NO TEXT')}'")
                        
                        # Verify this matches the expected structure for client parsing
                        if part.get('text') == 'OK':
                            print("✅ OK message format is correct!")
                        else:
                            print(f"❌ Expected 'OK' but got: '{part.get('text')}'")
    except Exception as e:
        print(f"❌ Error parsing JSON: {e}")
    
    print(f"\n🔍 Summary:")
    print(f"   - Enhanced API endpoint: /v2/echat")
    print(f"   - Basic API endpoint: /v2/chat (no OK message)")
    print(f"   - Client should now call enhanced endpoint")

if __name__ == "__main__":
    test_ok_message_format()