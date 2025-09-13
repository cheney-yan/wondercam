# V2 API Debug Guide

## Issue: V2 API Shows as Unhealthy

The V2 API status indicator is showing "unhealthy" (red dot). Here are the likely causes and solutions:

### Root Cause Analysis

1. **Missing Next.js Rewrite Rule** ✅ **FIXED**
   - Added V2 API rewrite rule to `next.config.ts`
   - Frontend `/v2/*` requests now properly route to backend

2. **Backend Not Running** ⚠️ **LIKELY ISSUE**
   - V2 API endpoints exist but backend server may not be running
   - V2 routes need to be registered in FastAPI

3. **URL Configuration Mismatch** ⚠️ **POTENTIAL ISSUE**
   - Root `.env`: `http://api:8000/` (Docker)
   - App `.env`: `https://vertex.yan.today` (External)

### Debugging Steps

#### 1. Check Backend Server Status
```bash
# Test if backend is accessible
curl http://localhost:8000/health
# or 
curl https://vertex.yan.today/health

# Should return:
# {"status": "healthy", "service": "vertex-gemini-translator"}
```

#### 2. Test V2 API Endpoints
```bash
# Test V2 health endpoint
curl http://localhost:8000/v2/health
# or
curl https://vertex.yan.today/v2/health

# Should return:
# {"status": "healthy", "version": "v2", "features": [...]}
```

#### 3. Check V2 API Capabilities
```bash
# Test V2 capabilities
curl http://localhost:8000/v2/capabilities
# or
curl https://vertex.yan.today/v2/capabilities

# Should return:
# {"version": "v2", "message_types": ["text", "image", "voice"], ...}
```

#### 4. Test Frontend to Backend Connection
Open browser dev tools and check:
- Network tab for failed `/v2/*` requests
- Console for V2 API initialization errors
- API Status Indicator details

### Fixes Applied

1. **✅ Next.js Rewrite Rule Added**
   ```typescript
   // next.config.ts
   {
     source: '/v2/:path*',
     destination: `${process.env.NEXT_PUBLIC_BACKEND_API_HOST}/v2/:path*`,
   }
   ```

2. **✅ Fixed Async Response Handling**
   ```python
   # v2_api.py - Fixed httpx async response
   error_text = await response.atext()  # Was: response.text
   ```

### Current Status

- **Frontend**: ✅ V2 integration complete with rewrite rules
- **Backend**: ⚠️ V2 API endpoints implemented but may not be running
- **Health Check**: ❌ Failing because backend V2 endpoints unreachable

### Next Steps to Fix

#### Option 1: Start Backend Server (If Not Running)
```bash
cd api
DEBUG=True uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Option 2: Use Docker (If Using Docker Setup)
```bash
# Development mode with hot reload
docker-compose -f docker-compose.dev.yml up --build
```

#### Option 3: Check Backend Logs
```bash
# Check for V2 API import/startup errors
docker-compose logs api
# or check FastAPI logs when running locally
```

### Expected Behavior After Fix

1. **API Status Indicator**: Should show green dot for "v2"
2. **Browser Console**: Should show V2 API initialization success
3. **Network Requests**: Should see successful `/v2/health` and `/v2/capabilities` calls
4. **Chat/Photo Functions**: Should work with V2 API and show "🚀 Using V2 API" logs

### Verification Commands

```bash
# 1. Backend health
curl -v http://localhost:8000/health

# 2. V2 specific endpoints
curl -v http://localhost:8000/v2/health
curl -v http://localhost:8000/v2/capabilities

# 3. Full API info (should show both v1beta and v2)
curl -v http://localhost:8000/

# 4. Test with authentication (replace with actual JWT)
curl -v -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/v2/chat \
  -d '{"messages":[{"role":"user","content":[{"type":"text","data":"Hello"}]}],"stream":true}'
```

### Environment Variables Check

Make sure your environment has:
```bash
# Required for V2 to work
NEXT_PUBLIC_USE_V2_API=true
NEXT_PUBLIC_V2_API_FALLBACK=true
NEXT_PUBLIC_BACKEND_API_HOST=http://localhost:8000
# (or whatever your backend URL is)
```

The main issue is likely that the backend server needs to be started with the V2 API routes loaded, or there's a connectivity issue between frontend and backend.