# 🔄 Vertex AI Compatible Streaming Implementation

## Critical Requirement

All V2 API responses must be formatted in **Vertex AI streaming format** so the frontend can process them seamlessly without knowing the difference between:
- Our immediate responses
- Our status updates  
- Our direct replies
- Real Vertex AI responses

## Current Frontend Processing

Looking at `app/lib/ai-service-v2.ts`, the frontend expects this format:

```javascript
// Frontend expects this Vertex AI streaming format
{
  "candidates": [
    {
      "content": {
        "parts": [
          {"text": "response text here"}
        ]
      }
    }
  ]
}
```

## Enhanced Implementation with Vertex AI Format

### 1. **Vertex AI Response Formatter**

```python
# Add to api/v2_api.py

import json
from typing import Dict, Any, Optional

class VertexAIResponseFormatter:
    """Formats all responses in Vertex AI streaming format for frontend compatibility"""
    
    @staticmethod
    def format_text_chunk(text: str, is_final: bool = False) -> str:
        """Format text as Vertex AI streaming chunk"""
        
        vertex_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": text}
                        ]
                    },
                    "finishReason": "STOP" if is_final else None,
                    "index": 0,
                    "safetyRatings": [
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH", 
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "probability": "NEGLIGIBLE"
                        }
                    ]
                }
            ]
        }
        
        # Remove finishReason if not final to match streaming format
        if not is_final:
            del vertex_response["candidates"][0]["finishReason"]
        
        return f"data: {json.dumps(vertex_response)}\n\n"
    
    @staticmethod
    def format_image_chunk(image_data: str, is_final: bool = False) -> str:
        """Format image as Vertex AI streaming chunk"""
        
        vertex_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": image_data
                                }
                            }
                        ]
                    },
                    "finishReason": "STOP" if is_final else None,
                    "index": 0,
                    "safetyRatings": [
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_HARASSMENT", 
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "probability": "NEGLIGIBLE"
                        }
                    ]
                }
            ]
        }
        
        if not is_final:
            del vertex_response["candidates"][0]["finishReason"]
        
        return f"data: {json.dumps(vertex_response)}\n\n"
    
    @staticmethod  
    def format_system_status(status_text: str) -> str:
        """Format system status as Vertex AI text chunk"""
        return VertexAIResponseFormatter.format_text_chunk(status_text, is_final=False)
    
    @staticmethod
    def format_final_response(text: str) -> str:
        """Format final response with proper finish reason"""
        return VertexAIResponseFormatter.format_text_chunk(text, is_final=True)

# Global formatter instance
formatter = VertexAIResponseFormatter()
```

### 2. **Updated V2 API Handler with Vertex AI Formatting**

```python
# Enhanced api/v2_api.py

async def stream_v2_response(request: V2ChatRequest, user: dict) -> AsyncGenerator[str, None]:
    """Optimized streaming with Vertex AI compatible format"""
    
    try:
        current_translator = get_translator()
        
        # Step 1: IMMEDIATE response in Vertex AI format
        logger.info("🚀 Sending immediate acknowledgment in Vertex AI format...")
        yield formatter.format_text_chunk("OK")
        
        # Step 2: Start background analysis
        logger.info("🧠 Starting background prompt analysis...")
        
        analysis_task = asyncio.create_task(
            run_background_analysis(request, current_translator)
        )
        
        # Step 3: Wait for analysis with timeout
        try:
            analysis_result = await asyncio.wait_for(analysis_task, timeout=2.0)
            logger.info(f"✅ Background analysis completed: {analysis_result.action}")
        except asyncio.TimeoutError:
            logger.warning("⏰ Analysis timeout, proceeding with pass-through")
            analysis_result = AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Analysis timed out for responsiveness"
            )
        
        # Step 4: Stream status update in Vertex AI format
        status_message = get_status_message(analysis_result)
        yield formatter.format_system_status(status_message)
        
        # Step 5: Handle analysis result
        if analysis_result.action == AnalysisAction.DIRECT_REPLY:
            # Stream direct reply as final Vertex AI response
            logger.info("🛑 Streaming direct reply in Vertex AI format")
            yield formatter.format_final_response(analysis_result.direct_reply)
            return
        
        # Step 6: Continue to Vertex AI (REFINE or PASS_THROUGH)
        if analysis_result.action == AnalysisAction.REFINE:
            # Apply refined prompt
            logger.info("✨ Applying refined prompt")
            apply_refined_prompt(request, analysis_result.refined_prompt)
        
        # Step 7: Stream from Vertex AI (already in correct format)
        logger.info("🎯 Starting Vertex AI streaming...")
        vertex_request = current_translator.v2_to_vertex(request)
        
        # Stream directly from Vertex AI - already in correct format
        async for vertex_chunk in stream_from_vertex_ai(vertex_request, current_translator):
            yield vertex_chunk
        
        logger.info("✅ Streaming completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Streaming error: {e}")
        # Format error as Vertex AI response
        error_message = f"I apologize, but I encountered an error processing your request. Please try again."
        yield formatter.format_final_response(error_message)

async def stream_from_vertex_ai(vertex_request: VertexRequest, translator: V2MessageTranslator) -> AsyncGenerator[str, None]:
    """Stream response from Vertex AI - passes through native format"""
    
    vertex_endpoint = translator.get_vertex_endpoint()
    access_token = translator.auth_handler.get_access_token()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        logger.info(f"🔗 Calling Vertex AI endpoint: {vertex_endpoint}?alt=sse")
        
        response = await client.post(
            f"{vertex_endpoint}?alt=sse",
            headers=headers,
            json=vertex_request.model_dump()
        )
        
        logger.info(f"📥 Vertex AI response status: {response.status_code}")
        
        if not response.is_success:
            error_text = response.text
            logger.error(f"❌ Vertex AI error: {response.status_code} - {error_text}")
            
            # Format error as Vertex AI response
            error_message = "I encountered an issue processing your request. Please try again."
            yield formatter.format_final_response(error_message)
            return
        
        # Stream Vertex AI response directly - already in correct format
        logger.info("🚀 Streaming Vertex AI response directly...")
        async for chunk in response.aiter_text():
            # Vertex AI chunks are already in the correct format
            yield chunk
```

### 3. **Frontend Compatibility Verification**

Looking at the frontend code in `app/lib/ai-service-v2.ts`, it processes responses like this:

```javascript
// From ai-service-v2.ts lines 282-295
else if ('candidates' in data && Array.isArray(data.candidates)) {
  for (const candidate of data.candidates) {
    if (candidate.content?.parts) {
      for (const part of candidate.content.parts) {
        if (part.text) {
          yield part.text;  // Our formatted text will work here
        } else if (part.inlineData?.data) {
          yield { type: 'image', data: part.inlineData.data };
        }
      }
    }
  }
}
```

Our formatted responses will work perfectly with this existing parsing logic!

### 4. **Example Streaming Flows**

#### **Vague Request → REFINE**
```javascript
// What the frontend receives:

// 1. Immediate response (Vertex AI format)
{
  "candidates": [
    {
      "content": {
        "parts": [{"text": "OK"}]
      },
      "index": 0,
      "safetyRatings": [...]
    }
  ]
}

// 2. Status update (Vertex AI format)  
{
  "candidates": [
    {
      "content": {
        "parts": [{"text": "I am generating an enhanced response based on your request..."}]
      },
      "index": 0,
      "safetyRatings": [...]
    }
  ]
}

// 3. Real Vertex AI response (native format)
{
  "candidates": [
    {
      "content": {
        "parts": [{"text": "I'd be happy to help you with a specific task..."}]
      },
      "finishReason": "STOP",
      "index": 0,
      "safetyRatings": [...]
    }
  ]
}
```

#### **Inappropriate Request → DIRECT_REPLY**
```javascript
// What the frontend receives:

// 1. Immediate response
{
  "candidates": [
    {
      "content": {
        "parts": [{"text": "OK"}]
      },
      "index": 0,
      "safetyRatings": [...]
    }
  ]
}

// 2. Status update
{
  "candidates": [
    {
      "content": {
        "parts": [{"text": "Let me help you with that directly..."}]
      },
      "index": 0,
      "safetyRatings": [...]
    }
  ]
}

// 3. Direct reply (final)
{
  "candidates": [
    {
      "content": {
        "parts": [{"text": "I cannot assist with activities that might violate privacy or security..."}]
      },
      "finishReason": "STOP",
      "index": 0,
      "safetyRatings": [...]
    }
  ]
}
```

### 5. **Configuration Options**

```python
# api/config.py

class Settings(BaseSettings):
    # ... existing settings
    
    # Vertex AI compatibility settings
    vertex_ai_format_enabled: bool = True
    include_safety_ratings: bool = True
    include_finish_reason: bool = True
    
    # Response format settings
    immediate_response_text: str = "OK"
    status_messages: Dict[str, str] = {
        "refine": "I am generating an enhanced response based on your request...",
        "direct_reply": "Let me help you with that directly...",
        "pass_through": "Processing your request...",
    }
    
    # Safety ratings (standard Vertex AI format)
    default_safety_ratings: List[Dict[str, str]] = [
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "probability": "NEGLIGIBLE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "NEGLIGIBLE"},
        {"category": "HARM_CATEGORY_HARASSMENT", "probability": "NEGLIGIBLE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "NEGLIGIBLE"}
    ]
```

### 6. **Testing Frontend Compatibility**

```javascript
// Test that all response types work with existing frontend parsing

// Test immediate response
const immediateResponse = {
  "candidates": [{"content": {"parts": [{"text": "OK"}]}, "index": 0}]
};

// Test status update
const statusResponse = {
  "candidates": [{"content": {"parts": [{"text": "Processing..."}]}, "index": 0}]
};

// Test direct reply
const directReply = {
  "candidates": [{"content": {"parts": [{"text": "I cannot help with that."}]}, "finishReason": "STOP", "index": 0}]
};

// All should parse correctly with existing frontend code:
for (const candidate of response.candidates) {
  if (candidate.content?.parts) {
    for (const part of candidate.content.parts) {
      if (part.text) {
        console.log('Text:', part.text); // ✅ Works for all our formats
      }
    }
  }
}
```

## Benefits

### 1. **Seamless Frontend Compatibility**
- All responses use identical Vertex AI streaming format
- Existing frontend parsing logic works without changes
- No special handling needed for different response types

### 2. **Transparent Integration**
- Frontend cannot distinguish between our responses and Vertex AI responses
- Consistent user experience across all interaction types
- Natural streaming behavior maintained

### 3. **Future-Proof Design**
- Any Vertex AI format changes can be handled in the formatter
- Easy to extend for new response types (images, etc.)
- Maintains compatibility as Vertex AI evolves

This ensures perfect compatibility with your existing frontend while providing all the intelligent prompt analysis benefits transparently.