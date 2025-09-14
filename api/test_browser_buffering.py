#!/usr/bin/env python3
"""
Test to determine if browser buffering is preventing immediate OK delivery
Creates a minimal test server to isolate the buffering issue
"""

import asyncio
import json
import time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Enable CORS for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def immediate_test_stream():
    """Test stream that sends OK immediately with various techniques"""
    
    print(f"🚀 Starting immediate test stream at {time.time()}")
    
    # Technique 1: Immediate OK message
    ok_message = 'data: {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}\n\n'
    yield ok_message.encode('utf-8')
    print(f"✅ Sent OK at {time.time()}")
    
    # Technique 2: Multiple heartbeat comments to force browser parsing
    for i in range(5):
        heartbeat = f": heartbeat-{i+1}\n\n"
        yield heartbeat.encode('utf-8')
        await asyncio.sleep(0.001)
        print(f"💓 Sent heartbeat {i+1} at {time.time()}")
    
    # Technique 3: Small data chunks to maintain stream
    for i in range(3):
        chunk = f'data: {{"status": "processing", "step": {i+1}}}\n\n'
        yield chunk.encode('utf-8')
        await asyncio.sleep(0.1)
        print(f"📦 Sent chunk {i+1} at {time.time()}")
    
    # Final message
    final_message = 'data: {"candidates": [{"content": {"parts": [{"text": "Complete"}]}}]}\n\n'
    yield final_message.encode('utf-8')
    print(f"✅ Sent final message at {time.time()}")

@app.get("/test-immediate")
async def test_immediate_response():
    """Test endpoint for immediate response"""
    return StreamingResponse(
        immediate_test_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/test-html")
async def test_html():
    """Test HTML page to verify immediate response in browser"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Immediate OK Test</title>
    <style>
        body { font-family: monospace; padding: 20px; }
        .log { margin: 5px 0; padding: 5px; background: #f0f0f0; }
        .ok { background: #d4edda; }
        .heartbeat { background: #fff3cd; }
        .chunk { background: #d1ecf1; }
        .final { background: #f8d7da; }
    </style>
</head>
<body>
    <h1>🧪 Immediate OK Message Test</h1>
    <p>This test will show when messages are received by the browser.</p>
    <p><strong>Expected:</strong> OK message should appear within 50ms of clicking Start Test</p>
    
    <button onclick="startTest()">Start Test</button>
    <button onclick="clearLogs()">Clear Logs</button>
    
    <div id="logs"></div>
    
    <script>
        function log(message, type = 'log') {
            const timestamp = new Date().toISOString().slice(11, 23);
            const div = document.createElement('div');
            div.className = `log ${type}`;
            div.textContent = `[${timestamp}] ${message}`;
            document.getElementById('logs').appendChild(div);
            console.log(`[${timestamp}] ${message}`);
        }
        
        function clearLogs() {
            document.getElementById('logs').innerHTML = '';
        }
        
        async function startTest() {
            clearLogs();
            const startTime = Date.now();
            log('🚀 Starting immediate response test...', 'log');
            
            try {
                const response = await fetch('/test-immediate');
                
                if (!response.ok) {
                    log(`❌ Error: ${response.status} - ${response.statusText}`, 'log');
                    return;
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let messageCount = 0;
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const currentTime = Date.now();
                    const elapsed = currentTime - startTime;
                    messageCount++;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.startsWith('data:')) {
                            const jsonStr = line.substring(5).trim();
                            if (jsonStr) {
                                try {
                                    const data = JSON.parse(jsonStr);
                                    if (data.candidates && data.candidates[0]?.content?.parts?.[0]?.text === 'OK') {
                                        log(`✅ OK MESSAGE RECEIVED at +${elapsed}ms!`, 'ok');
                                    } else if (data.status === 'processing') {
                                        log(`📦 Processing step ${data.step} at +${elapsed}ms`, 'chunk');
                                    } else if (data.candidates && data.candidates[0]?.content?.parts?.[0]?.text === 'Complete') {
                                        log(`🏁 Final message at +${elapsed}ms`, 'final');
                                    } else {
                                        log(`📨 Message #${messageCount} at +${elapsed}ms: ${JSON.stringify(data)}`, 'log');
                                    }
                                } catch (e) {
                                    log(`⚠️ Parse error at +${elapsed}ms: ${jsonStr}`, 'log');
                                }
                            }
                        } else if (line.startsWith(':')) {
                            log(`💓 Heartbeat at +${elapsed}ms: ${line}`, 'heartbeat');
                        }
                    }
                }
                
                log('✅ Test completed', 'log');
                
            } catch (error) {
                log(`❌ Test failed: ${error.message}`, 'log');
            }
        }
    </script>
</body>
</html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)

if __name__ == "__main__":
    print("🧪 Starting Browser Buffering Test Server")
    print("📍 Open http://localhost:8001/test-html in your browser")
    print("🎯 Click 'Start Test' to verify immediate OK delivery")
    print("💡 If OK appears within 50ms, server streaming works correctly")
    print("   If OK is delayed, the issue is browser/network buffering")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)