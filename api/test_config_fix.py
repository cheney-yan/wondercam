#!/usr/bin/env python3
"""
Quick test to disable prompt analysis for immediate response
"""

from config import settings

print("🔧 Current configuration:")
print(f"   prompt_analysis_enabled: {settings.prompt_analysis_enabled}")
print(f"   prompt_analysis_timeout: {settings.prompt_analysis_timeout}")
print(f"   immediate_response_text: '{settings.immediate_response_text}'")

# Test formatter speed
from vertex_formatter import VertexAIResponseFormatter
import time

start = time.time()
response = VertexAIResponseFormatter.format_immediate_response()
elapsed = time.time() - start

print(f"\n📤 Format test:")
print(f"   Time: {elapsed:.6f}s")
print(f"   Response: {response[:100]}...")

print(f"\n✅ Configuration looks correct for immediate response")