# 🚀 SSE (Server-Sent Events) Streaming Implementation Guide

## Overview

This document explains the complete SSE streaming implementation in WonderCam V2 API, focusing on real-time delivery through direct API connections.

## Architecture

### Components
- **API Server**: FastAPI with uvicorn (Port 18000)
- **Frontend**: Next.js (Port 3011)
- **Client Libraries**: Direct API connection bypassing Next.js proxy

## Critical Issues & Solutions

### Root Cause: Next.js Proxy Buffering

**Primary Issue**: Next.js development server was proxying `/v2/echat` requests and introducing significant buffering, causing 3027-byte chunk accumulation before client delivery.

**Impact**: Despite server sending OK messages in 51ms, clients experienced delayed responses waiting for large chunks.

**Solution**: Bypass Next.js proxy entirely with direct API connections.

**Before (Buffered via Next.js Proxy)**:
```javascript
const response = await fetch('/v2/echat', { // Goes through Next.js proxy
    method: 'POST',
    headers: { /* ... */ },
    body: JSON.stringify(payload)
});
```

**After (Direct API Connection)**:
```javascript
const response = await fetch('http://localhost:18000/v2/echat', { // Direct connection
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream',
    },
    body: JSON.stringify(payload)
});
```

### Secondary Issue: Uvicorn Buffer Threshold (Resolved)

**Previous Problem**: Uvicorn internal buffer threshold of ~512-1024 bytes before network flush
**Previous Solution**: SSE comment padding to exceed buffer threshold
**Current Status**: **No longer needed** - Direct connections eliminate buffering concerns

The padding workaround is no longer required since direct API connections bypass all proxy buffering layers.

## Implementation Details

### Server-Side SSE Format

```
data: {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}

data: {"candidates": [{"content": {"parts": [{"text": "Streaming response..."}]}}]}

data: [DONE]

```

### Client-Side Processing

The client receives SSE events and processes them line by line:

```javascript
const reader = response.body?.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value, { stream: true });
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] Received ${chunk.length} bytes`);
  
  buffer += chunk;
  const lines = buffer.split('\n');
  buffer = lines.pop() || '';

  for (const line of lines) {
    if (line.startsWith('data:')) {
      const jsonStr = line.substring(5).trim();
      const data = JSON.parse(jsonStr);
      // Process SSE data immediately - no delay from buffering
    }
  }
}
```

## Performance Results

### Before Direct Connection Fix
- **Server**: OK sent in 51ms ✅
- **Next.js Proxy**: Buffers into 3027-byte chunks ❌
- **Client**: Waits for large accumulated chunks ❌
- **User Experience**: Delayed, chunky responses

### After Direct Connection Implementation
- **Server**: OK sent in 51ms ✅
- **Network**: Direct TCP connection ✅
- **Client**: Receives OK immediately in 51ms ✅
- **User Experience**: True real-time streaming with immediate feedback

## Critical Files

### Server-Side Implementation

#### [`api/v2_api.py`](api/v2_api.py) - Standard V2 API
```python
# Clean streaming without padding complexity
async for chunk in response.aiter_text():
    yield chunk  # Direct chunk streaming
```

#### [`api/v2_api_enhanced.py`](api/v2_api_enhanced.py) - Enhanced V2 API
```python
# Simplified immediate OK response
ok_response = formatter.format_immediate_response()
yield ok_response.encode('utf-8')

# Clean Vertex AI chunk streaming
async for vertex_chunk in stream_from_vertex_ai(vertex_request, current_translator):
    yield vertex_chunk.encode('utf-8')
```

#### [`api/main.py`](api/main.py) - Main API Server
- Removed unnecessary SSE padding helper functions
- Clean, simplified streaming architecture
- Focus on direct connections rather than buffering workarounds

### Client-Side Implementation

#### [`app/lib/ai-service-v2.ts`](app/lib/ai-service-v2.ts) - Main AI Service
```javascript
// Line 218: Direct API connection bypassing Next.js proxy
const response = await fetch('http://localhost:18000/v2/echat', {

// Lines 254-326: Comprehensive SSE processing with timestamp logging
```

#### [`app/lib/ai-service-eventsource.ts`](app/lib/ai-service-eventsource.ts) - EventSource Implementation
```javascript
// Line 122: Direct EventSource connection
const url = `http://localhost:18000/v2/echat?data=${encodedRequest}`;
```

## Debugging Features

### Server-Side Logging
```python
print(f"✅ Sent OK with padding at {time.time()}")
print(f"📦 Sent chunk {i+1} at {time.time()}")
```

### Client-Side Timestamp Logging
```javascript
const timestamp = new Date().toISOString();
const relativeTime = Date.now();
console.log(`📨 V2 API [${timestamp}]: Received raw chunk at ${relativeTime}`);
console.log(`📡 V2 API [${timestamp}]: Processing SSE line`);
console.log(`📨 V2 API [${timestamp}]: Received text chunk: ${part.text}`);
```

## SSE Specification Compliance

The implementation follows the [Server-Sent Events W3C Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html):

- **Data lines**: `data: content\n\n`
- **Comment lines**: `: comment\n\n` (used for padding)
- **Event separation**: Double newline `\n\n`
- **UTF-8 encoding**: All content encoded as UTF-8

## Docker Configuration

### API Server (Port 18000)
```yaml
api:
  ports:
    - "18000:8000"
  environment:
    - HOST=0.0.0.0
    - PORT=8000
```

### Frontend (Port 3011)  
```yaml
app:
  ports:
    - "3011:3000"
  environment:
    - NEXT_PUBLIC_BACKEND_API_HOST=${NEXT_PUBLIC_BACKEND_API_HOST}
```

## Troubleshooting

### Issue: Large chunks (3000+ bytes) received at client
**Cause**: Using Next.js proxy instead of direct API connection
**Solution**: Ensure client uses direct API connection (`http://localhost:18000/v2/echat`)

### Issue: Delayed OK message delivery
**Cause**: Proxy buffering or indirect connection routing
**Solution**: Verify direct API connection bypasses all proxy layers

### Issue: SSE events not parsing correctly
**Cause**: Missing double newlines or incorrect data format
**Solution**: Ensure proper SSE format with `data:` prefix and `\n\n` separators

### Issue: Connection timeouts or failures
**Cause**: API server not running or incorrect endpoint URL
**Solution**: Verify API server is running on port 18000 and endpoint URLs are correct

## Best Practices

1. **Direct API connections**: Always bypass proxy layers for real-time streaming
2. **Immediate acknowledgment**: Send OK messages without delay
3. **Clean streaming**: Avoid unnecessary padding and heartbeat complications
4. **Proper error handling**: Handle connection drops and reconnection gracefully
5. **Comprehensive logging**: Include detailed timestamp logging for debugging
6. **Production security**: Use HTTPS and proper CORS configuration in production

## Production Considerations

### Nginx Configuration (if used)
```nginx
location /v2/ {
    proxy_pass http://api:8000;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header X-Accel-Buffering no;
}
```

### Load Balancer Settings
- Disable response buffering
- Set appropriate timeouts for long-running streams
- Enable sticky sessions if using multiple API instances

### Monitoring
- Track SSE connection counts
- Monitor average response times
- Alert on excessive buffering delays
- Log SSE parsing errors

## Security Considerations

- **Authentication**: JWT tokens in Authorization header
- **CORS**: Properly configured for cross-origin requests
- **Rate Limiting**: Prevent SSE connection abuse
- **Input Validation**: Sanitize all streaming content

## Testing

### Manual Testing
```bash
curl -N -H "Accept: text/event-stream" http://localhost:18000/v2/echat
```

### Automated Testing  
- Unit tests for SSE formatting functions
- Integration tests for end-to-end streaming
- Performance tests for latency measurements
- Browser compatibility testing

This implementation ensures true real-time SSE streaming with immediate OK message delivery and optimal user experience.