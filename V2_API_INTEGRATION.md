# WonderCam V2 API Integration Guide

## Overview

The V2 API provides a simplified, extensible interface alongside the existing v1beta API. Both APIs coexist and can be used interchangeably.

## Key Differences: V1Beta vs V2

| Feature | V1Beta | V2 |
|---------|--------|-----|
| **Authentication** | `x-goog-api-key: {jwt_token}` | `Authorization: Bearer {jwt_token}` |
| **Message Format** | Gemini-compatible JSON | Extensible message types |
| **Content Types** | Text + inline images | Text, Image, Voice (extensible) |
| **Preprocessing** | No | Yes - custom logic before AI |
| **API Complexity** | Complex frontend construction | Simple frontend, complex backend |
| **Streaming** | SSE with Gemini format | SSE with V2 format |

## V2 API Architecture

### Backend Components
- **v2_models.py**: Data structures and Pydantic models
- **v2_translator.py**: Converts V2 ↔ Vertex AI formats
- **v2_api.py**: FastAPI endpoints with streaming support
- **main.py**: Updated to include V2 routes

### Frontend Components  
- **ai-service-v2.ts**: Simplified V2 client
- **ai-service.ts**: Existing V1Beta client (unchanged)

## Message Type System

### Text Message
```typescript
{
  role: "user",
  content: [{
    type: "text",
    data: "Hello, can you help me?"
  }]
}
```

### Image Message
```typescript
{
  role: "user", 
  content: [
    {
      type: "text",
      data: "What's in this image?"
    },
    {
      type: "image",
      data: "data:image/jpeg;base64,/9j/4AAQ...",
      mime_type: "image/jpeg"
    }
  ]
}
```

### Voice Message (Future)
```typescript
{
  role: "user",
  content: [
    {
      type: "text", 
      data: "Here's my voice message"
    },
    {
      type: "voice",
      data: "data:audio/webm;base64,GkXf...",
      mime_type: "audio/webm"
    }
  ]
}
```

## Frontend Integration

### Using V2 API (Recommended for new features)

```typescript
import { aiServiceV2 } from '@/lib/ai-service-v2';

// Simple text chat
async function simpleChat() {
  const messages = [
    aiServiceV2.createTextMessage("Hello, how are you?")
  ];

  for await (const chunk of aiServiceV2.chatStream(messages, 'en')) {
    if (chunk.type === 'text') {
      console.log('AI:', chunk.data);
    } else if (chunk.type === 'image') {
      console.log('AI generated image:', chunk.data);
    }
  }
}

// Photo analysis
async function analyzePhoto(photo: CapturedPhoto) {
  for await (const chunk of aiServiceV2.analyzePhoto(
    photo, 
    "What's interesting about this image?", 
    'en'
  )) {
    if (typeof chunk === 'string') {
      console.log('AI:', chunk);
    } else if (chunk.type === 'image') {
      console.log('AI generated image:', chunk.data);
    }
  }
}
```

### Using V1Beta API (Existing code unchanged)

```typescript 
import { aiService } from '@/lib/ai-service';

// Existing code continues to work
for await (const chunk of aiService.analyzePhoto(photo, message, language)) {
  // Handle chunks as before
}
```

## Backend Preprocessing

The V2 API supports preprocessing logic that can interact with the client before calling Vertex AI:

```python
async def preprocess_request(self, request: V2ChatRequest):
    """Custom preprocessing logic"""
    latest_message = request.messages[-1]
    text_contents = [c for c in latest_message.content if c.type == MessageType.TEXT]
    
    if text_contents:
        text = text_contents[0].data.lower()
        
        # Custom logic examples
        if "generate" in text and "image" in text:
            yield V2ResponseChunk(
                type="system",
                content={
                    "type": "preprocessing",
                    "content": "I'll generate an image. This costs 2 credits.",
                    "action": "confirm_generation"
                }
            )
```

## Migration Strategy

1. **Phase 1**: Deploy V2 API alongside V1Beta (current)
2. **Phase 2**: Update new features to use V2 API
3. **Phase 3**: Gradually migrate existing features
4. **Phase 4**: Deprecate V1Beta (future)

## API Endpoints

### V1Beta (Existing)
- `POST /v1beta/models/{model}:{action}` - Gemini-compatible endpoint

### V2 (New)
- `POST /v2/chat` - Unified chat endpoint
- `GET /v2/health` - V2 health check  
- `GET /v2/capabilities` - API capabilities

### Root
- `GET /` - Shows both API versions

## Testing V2 API

### Backend Test
```bash
# Start the API server
cd api
DEBUG=True uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Test V2 endpoint
curl -X POST http://localhost:8000/v2/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": [{
        "type": "text",
        "data": "Hello, world!"
      }]
    }],
    "language": "en",
    "stream": true
  }'
```

### Frontend Integration Test
```typescript
// Test V2 capabilities
const capabilities = await aiServiceV2.getCapabilities();
console.log('V2 API supports:', capabilities);

// Test simple chat
for await (const response of aiServiceV2.simpleChat("Hello!")) {
  console.log('Response:', response);
}
```

## Benefits of V2 API

### For Frontend Developers
- **Simpler Integration**: One unified endpoint vs. multiple Gemini endpoints
- **Type Safety**: Strong TypeScript interfaces
- **Extensible**: Easy to add new message types (voice, video, documents)
- **Preprocessing**: Backend can handle complex logic before AI calls

### For Backend Developers  
- **Extensible Architecture**: Easy to add new message types and processing logic
- **Custom Logic**: Preprocessing allows custom business logic
- **Better Error Handling**: Structured error responses
- **Future-Proof**: Designed for expansion

## Current Status
- ✅ V2 API implemented and deployed alongside V1Beta
- ✅ Message type system (text, image, voice structure)
- ✅ Authentication updated to Authorization header
- ✅ Frontend V2 client created
- ✅ Preprocessing capability added
- 🔄 Testing and validation in progress
- 📋 Ready for integration testing

Both APIs are now available and can be used side by side for comparison and gradual migration.