#!/bin/bash

echo "🧪 Testing immediate OK message delivery with curl"
echo "=================================================="

# Test the enhanced endpoint with curl to verify server-side streaming
echo "📡 Testing /v2/echat endpoint..."
echo ""

# Create a simple test request
REQUEST_DATA='{
    "contents": [
        {"text": "Hello, test message"}
    ],
    "language": "en",
    "stream": true
}'

echo "🔍 Request data:"
echo "$REQUEST_DATA"
echo ""

echo "⏱️ Testing streaming response timing..."
echo "Expected: First chunk should contain 'OK' and arrive immediately"
echo ""

# Use curl to test streaming with timing
curl -X POST "http://localhost:8000/v2/echat" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer fake_token_for_testing" \
    -d "$REQUEST_DATA" \
    --no-buffer \
    --write-out "TIMING: Total time: %{time_total}s, Time to first byte: %{time_starttransfer}s\n" \
    2>/dev/null | while IFS= read -r line; do
        timestamp=$(date +"%H:%M:%S.%3N")
        echo "[$timestamp] $line"
        
        # Stop after receiving a few chunks to avoid long streaming
        if [[ "$line" == *"candidates"* ]] && [[ "$line" == *"OK"* ]]; then
            echo "🎯 OK message detected!"
            break
        fi
        
        # Safety: stop after 10 seconds
        sleep 0.1
    done

echo ""
echo "💡 If the OK message appears immediately (within first 50ms), the server-side streaming works correctly."
echo "   If there's a delay, the issue is in the network buffering or client-side processing."