# V2 Frontend Integration Testing Guide

## Testing Setup Complete ✅

The frontend has been successfully refactored to use the V2 API with fallback support. Here's what's been implemented:

### Environment Configuration
- **`.env`** updated with V2 API flags:
  - `NEXT_PUBLIC_USE_V2_API=true` - Enables V2 API by default
  - `NEXT_PUBLIC_V2_API_FALLBACK=true` - Falls back to V1Beta on V2 failure
  - `NEXT_PUBLIC_API_VERSION=v2` - Sets preferred API version

### Frontend Components Updated
- **Main WonderCam Page** (`/app/wondercam/page.tsx`):
  - Imports unified AI service
  - Replaces direct AI service calls with unified service
  - Clears conversation history on new photo sessions
  - Initializes API and logs configuration on startup

- **Unified AI Service** (`/lib/ai-service-unified.ts`):
  - Automatically chooses V2 or V1Beta based on environment
  - Provides fallback from V2 to V1Beta on errors
  - Maintains conversation history for V2 API
  - Health checking for both API versions

- **API Status Indicator** (`/components/api-status-indicator.tsx`):
  - Shows current API version and health status
  - Real-time monitoring of both V1Beta and V2 APIs
  - Environment configuration display
  - Available features listing

## Testing the Integration

### 1. Visual Verification
When you start the app, you should see:
- **Top-left corner**: API status indicator showing "v2" with green dot
- **Browser console**: Initialization logs showing V2 API usage
- **Clicking status indicator**: Shows detailed API health and features

### 2. Console Verification
Look for these console logs:
```
🔧 Initializing AI Service...
✅ AI Service initialized: { version: "v2", capabilities: [...], health: {...} }
🚀 Using V2 API for photo analysis
✅ Using unified AI service (v2)
```

### 3. Feature Testing
Test these scenarios to verify V2 integration:

#### Photo Analysis
1. **Capture/upload a photo**
2. **Send message**: "What do you see?"
3. **Expected**: Console shows "🚀 Using V2 API for photo analysis"
4. **Response**: Should work normally with AI analysis

#### Image Generation
1. **Start direct chat** (without photo)
2. **Send message**: "Draw a sunset over mountains"
3. **Expected**: Console shows "🎨 Using V2 API for image generation"
4. **Response**: Should generate an image

#### Conversation Continuation
1. **After initial photo/chat**
2. **Send follow-up message**: "Tell me more"
3. **Expected**: Console shows "💬 Using V2 API for conversation continuation"
4. **Response**: Should maintain context

### 4. Fallback Testing
To test V2 → V1Beta fallback:

1. **Temporarily break V2**: Set `NEXT_PUBLIC_BACKEND_API_HOST` to invalid URL
2. **Try photo analysis**: Should show fallback logs
3. **Expected console**:
   ```
   ⚠️ V2 API failed for photo analysis: [error]
   🔄 Falling back to V1 API
   📡 Using V1 API for photo analysis
   ```

### 5. Environment Testing
Test different configurations:

#### V1Beta Only
```bash
NEXT_PUBLIC_USE_V2_API=false
NEXT_PUBLIC_V2_API_FALLBACK=false
NEXT_PUBLIC_API_VERSION=v1beta
```
Expected: Status shows "v1beta", all operations use V1Beta

#### V2 with Fallback Disabled
```bash
NEXT_PUBLIC_USE_V2_API=true
NEXT_PUBLIC_V2_API_FALLBACK=false
```
Expected: V2 failures throw errors instead of falling back

## API Comparison During Testing

### Request Headers
- **V1Beta**: Uses `x-goog-api-key: {jwt_token}`
- **V2**: Uses `Authorization: Bearer {jwt_token}`

### Request Endpoints
- **V1Beta**: `/v1beta/models/gemini-2.5-flash-image-preview:streamGenerateContent`
- **V2**: `/v2/chat`

### Message Format
- **V1Beta**: Gemini-compatible JSON structure
- **V2**: Extensible message content array

### Network Tab Verification
1. **Open DevTools** → Network tab
2. **Perform AI actions** (photo analysis, chat)
3. **Check requests**:
   - V2 usage: Look for `POST /v2/chat` with `Authorization: Bearer`
   - V1 fallback: Look for `POST /v1beta/models/` with `x-goog-api-key`

## Known Behaviors

### Conversation History
- **V2 API**: Maintains internal conversation history across turns
- **V1Beta**: Reconstructs history from ChatMessage array
- **New Photo**: History cleared automatically

### Error Handling
- **V2 Failures**: Fall back to V1Beta if enabled
- **Authentication**: Both APIs use same JWT token
- **Network Errors**: Retry logic depends on underlying service

### Performance
- **V2 API**: May have slight overhead from preprocessing
- **Fallback**: Adds latency when V2 fails but ensures reliability
- **Status Indicator**: Updates every 30 seconds

## Troubleshooting

### V2 API Not Working
1. Check environment variables are set correctly
2. Verify backend is running and accessible
3. Check network tab for failed `/v2/*` requests
4. Look for fallback logs in console

### Status Indicator Shows Red
1. Check API health in status indicator details
2. Verify backend services are running
3. Check authentication/JWT token validity
4. Review network connectivity

### No API Version Change
1. Restart development server after changing `.env`
2. Clear browser cache/localStorage
3. Check environment variable names are correct
4. Verify no TypeScript compilation errors

## Next Steps

1. **Monitor Performance**: Compare V2 vs V1Beta response times
2. **Test Edge Cases**: Network failures, token expiry, large images
3. **User Testing**: Verify no user-facing regressions
4. **Gradual Rollout**: Consider feature flags for production deployment

The V2 integration is now complete and ready for testing! 🎉