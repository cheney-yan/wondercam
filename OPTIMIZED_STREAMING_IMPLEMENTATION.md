# 🚀 Optimized Streaming Implementation - Immediate Response Design

## Overview

This enhanced design provides **immediate user feedback** while performing prompt analysis in the background, creating a seamless streaming experience without the user knowing about interception.

## Streaming Flow Architecture

```mermaid
graph TD
    A[User Request] --> B[V2 API Receives Request]
    B --> C[Immediate Stream: "OK"]
    B --> D[Start Background Analysis]
    C --> E[User Sees Instant Response]
    D --> F{Analysis Result}
    F -->|REFINE| G[Stream: "I am generating enhanced response..."]
    F -->|DIRECT_REPLY| H[Stream: "Let me help with that..."]  
    F -->|PASS_THROUGH| I[Stream: "Processing your request..."]
    G --> J[Continue to Vertex AI with Refined Prompt]
    H --> K[Stream Direct Reply]
    I --> L[Continue to Vertex AI with Original Prompt]
    J --> M[Stream Vertex AI Response]
    L --> M
    K --> N[Complete]
    M --> N
```

## Key Changes

### 1. **Parallel Processing Architecture**

Instead of sequential preprocessing → Vertex AI, we now have:
- **Immediate response** streaming starts
- **Background prompt analysis** runs in parallel
- **Status streaming** updates user based on analysis result
- **Seamless continuation** to final response

### 2. **Enhanced V2 API Handler**

```python
# Enhanced api/v2_api.py

import asyncio
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

async def stream_v2_response(request: V2ChatRequest, user: dict) -> AsyncGenerator[str, None]:
    """Optimized streaming V2 API with immediate response and background analysis"""
    
    try:
        current_translator = get_translator()
        
        # Step 1: IMMEDIATE response to user
        logger.info("🚀 Sending immediate acknowledgment...")
        immediate_response = V2ResponseChunk(
            type="text",
            content="OK",
            is_final=False,
            metadata={
                "source": "immediate_response",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        yield f"data: {json.dumps(immediate_response.model_dump())}\n\n"
        
        # Step 2: Start background analysis while preparing for streaming
        logger.info("🧠 Starting background prompt analysis...")
        
        # Create analysis task (non-blocking)
        analysis_task = asyncio.create_task(
            run_background_analysis(request, current_translator)
        )
        
        # Step 3: Wait for analysis with timeout (max 2 seconds for responsiveness)
        try:
            analysis_result = await asyncio.wait_for(analysis_task, timeout=2.0)
            logger.info(f"✅ Background analysis completed: {analysis_result.action}")
        except asyncio.TimeoutError:
            logger.warning("⏰ Analysis timeout, proceeding with pass-through")
            analysis_result = AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Analysis timed out for responsiveness"
            )
        
        # Step 4: Stream status update based on analysis
        status_message = get_status_message(analysis_result)
        status_chunk = V2ResponseChunk(
            type="text",
            content=status_message,
            is_final=False,
            metadata={
                "source": "analysis_status",
                "analysis_action": analysis_result.action.value,
                "confidence": getattr(analysis_result, 'confidence', 0.0)
            }
        )
        yield f"data: {json.dumps(status_chunk.model_dump())}\n\n"
        
        # Step 5: Handle analysis result
        if analysis_result.action == AnalysisAction.DIRECT_REPLY:
            # Stream direct reply immediately
            logger.info("🛑 Streaming direct reply")
            final_chunk = V2ResponseChunk(
                type="text",
                content=analysis_result.direct_reply,
                is_final=True,
                metadata={
                    "source": "direct_reply",
                    "analysis_confidence": analysis_result.confidence
                }
            )
            yield f"data: {json.dumps(final_chunk.model_dump())}\n\n"
            return
        
        # Step 6: Continue to Vertex AI (REFINE or PASS_THROUGH)
        if analysis_result.action == AnalysisAction.REFINE:
            # Apply refined prompt
            logger.info("✨ Applying refined prompt")
            apply_refined_prompt(request, analysis_result.refined_prompt)
        
        # Step 7: Stream from Vertex AI
        logger.info("🎯 Starting Vertex AI streaming...")
        vertex_request = current_translator.v2_to_vertex(request)
        
        async for vertex_chunk in stream_from_vertex_ai(vertex_request, current_translator):
            yield vertex_chunk
        
        logger.info("✅ Streaming completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Streaming error: {e}")
        error_chunk = V2ResponseChunk(
            type="error",
            content=f"Service error: {str(e)}",
            is_final=True
        )
        yield f"data: {json.dumps(error_chunk.model_dump())}\n\n"

async def run_background_analysis(request: V2ChatRequest, translator: V2MessageTranslator) -> 'AnalysisResult':
    """Run prompt analysis in background without blocking main response"""
    
    if not translator.prompt_analyzer or not settings.prompt_analysis_enabled:
        return AnalysisResult(action=AnalysisAction.PASS_THROUGH, reasoning="Analysis disabled")
    
    text_parts = [part.text for part in request.contents if part.text and part.text.strip()]
    if not text_parts:
        return AnalysisResult(action=AnalysisAction.PASS_THROUGH, reasoning="No text content")
    
    combined_text = " ".join(text_parts).strip()
    image_parts = [part for part in request.contents if part.inlineData and 
                  part.inlineData.get("mimeType", "").startswith("image/")]
    
    try:
        result = await translator.prompt_analyzer.analyze_prompt(
            combined_text,
            has_images=len(image_parts) > 0,
            context={"language": request.language}
        )
        return result
    except Exception as e:
        logger.error(f"Background analysis failed: {e}")
        return AnalysisResult(action=AnalysisAction.PASS_THROUGH, reasoning=f"Analysis error: {str(e)}")

def get_status_message(analysis_result: 'AnalysisResult') -> str:
    """Get appropriate status message based on analysis result"""
    
    if analysis_result.action == AnalysisAction.REFINE:
        return "I am generating an enhanced response based on your request..."
    elif analysis_result.action == AnalysisAction.DIRECT_REPLY:
        return "Let me help you with that directly..."
    else:  # PASS_THROUGH
        return "Processing your request..."

def apply_refined_prompt(request: V2ChatRequest, refined_prompt: str):
    """Apply refined prompt to the request"""
    for i, part in enumerate(request.contents):
        if part.text and part.text.strip():
            request.contents[i].text = refined_prompt
            logger.debug(f"Applied refined prompt: {refined_prompt[:100]}...")
            break

async def stream_from_vertex_ai(vertex_request: VertexRequest, translator: V2MessageTranslator) -> AsyncGenerator[str, None]:
    """Stream response from Vertex AI"""
    
    vertex_endpoint = translator.get_vertex_endpoint()
    access_token = translator.auth_handler.get_access_token()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{vertex_endpoint}?alt=sse",
            headers=headers,
            json=vertex_request.model_dump()
        )
        
        if not response.is_success:
            error_text = response.text
            logger.error(f"❌ Vertex AI error: {response.status_code} - {error_text}")
            
            error_chunk = V2ResponseChunk(
                type="error",
                content=f"AI service error: {error_text}",
                is_final=True
            )
            yield f"data: {json.dumps(error_chunk.model_dump())}\n\n"
            return
        
        # Stream Vertex AI response directly
        async for chunk in response.aiter_text():
            yield chunk
```

### 3. **Analysis Result Data Structure**

```python
# Enhanced api/prompt_analyzer.py

@dataclass
class AnalysisResult:
    """Simplified analysis result for background processing"""
    action: AnalysisAction
    refined_prompt: Optional[str] = None
    direct_reply: Optional[str] = None
    confidence: float = 0.0
    reasoning: Optional[str] = None

class PromptAnalyzer:
    """Enhanced for background processing"""
    
    async def analyze_prompt_background(
        self, 
        user_message: str, 
        has_images: bool = False,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 2.0  # Aggressive timeout for responsiveness
    ) -> AnalysisResult:
        """Fast background analysis with timeout optimization"""
        
        try:
            # Use more aggressive settings for background analysis
            analysis_response = await asyncio.wait_for(
                self._call_gemini_flash_fast(user_message, has_images),
                timeout=timeout
            )
            
            result = self._parse_analysis_response(analysis_response)
            
            return AnalysisResult(
                action=result.action,
                refined_prompt=result.refined_prompt,
                direct_reply=result.direct_reply,
                confidence=result.confidence,
                reasoning=result.reasoning
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"Analysis timeout after {timeout}s, using pass-through")
            return AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Analysis timeout for responsiveness",
                confidence=0.0
            )
        except Exception as e:
            logger.error(f"Background analysis error: {e}")
            return AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning=f"Analysis error: {str(e)}",
                confidence=0.0
            )
    
    async def _call_gemini_flash_fast(self, user_message: str, has_images: bool) -> str:
        """Optimized Gemini-Flash call for background processing"""
        
        # Use simplified prompt for faster processing
        if has_images:
            prompt = self._get_fast_image_prompt(user_message)
        elif self._is_creative_request(user_message):
            prompt = self._get_fast_creative_prompt(user_message)
        else:
            prompt = self._get_fast_analysis_prompt(user_message)
        
        # Faster generation config
        request_body = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Lower for faster, more consistent results
                "maxOutputTokens": 200,  # Smaller for speed
                "topP": 0.8,
                "topK": 20  # Reduced for speed
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"}
            ]
        }
        
        endpoint = f"https://aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{settings.vertex_ai_location}/publishers/google/models/gemini-2.5-flash:generateContent"
        
        headers = {
            "Authorization": f"Bearer {self.auth_handler.get_access_token()}",
            "Content-Type": "application/json"
        }
        
        # Use shorter timeout for background processing
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.post(endpoint, headers=headers, json=request_body)
            
            if not response.is_success:
                raise Exception(f"Gemini-Flash call failed: {response.status_code}")
            
            data = response.json()
            
            if data.get("candidates") and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if candidate.get("content", {}).get("parts"):
                    for part in candidate["content"]["parts"]:
                        if part.get("text"):
                            return part["text"]
            
            raise Exception("No valid response from Gemini-Flash")
    
    def _get_fast_analysis_prompt(self, user_message: str) -> str:
        """Simplified prompt for faster analysis"""
        return f"""Analyze quickly: "{user_message}"

Response format:
{{"action": "refine|direct_reply|pass_through", "refined_prompt": "...", "direct_reply": "...", "confidence": 0.X}}

Rules:
- REFINE: vague/unclear (enhance it)
- DIRECT_REPLY: inappropriate/harmful (polite refusal) 
- PASS_THROUGH: clear and appropriate (no change)"""
    
    def _get_fast_image_prompt(self, user_message: str) -> str:
        """Fast image analysis prompt"""
        return f"""Image request: "{user_message}"

{{"action": "refine|direct_reply|pass_through", "refined_prompt": "specific image analysis request", "direct_reply": "cannot analyze", "confidence": 0.X}}

Refine if unclear what to analyze. Direct reply if inappropriate."""
    
    def _get_fast_creative_prompt(self, user_message: str) -> str:
        """Fast creative request prompt"""
        return f"""Creative request: "{user_message}"

{{"action": "refine|pass_through", "refined_prompt": "enhanced creative prompt with specifics", "confidence": 0.X}}

Refine to add creative details (style, format, theme). Pass through if already detailed."""
```

### 4. **User Experience Flow Examples**

#### Example 1: Vague Request → REFINE
```
User: "help me"

Streaming Response:
1. "OK" (immediate, <10ms)
2. "I am generating an enhanced response based on your request..." (after analysis, ~500ms)
3. [AI response to refined prompt about specific help options] (vertex AI response)
```

#### Example 2: Inappropriate Request → DIRECT_REPLY
```
User: "hack someone's account"

Streaming Response:
1. "OK" (immediate, <10ms)  
2. "Let me help you with that directly..." (after analysis, ~500ms)
3. "I cannot assist with activities that might violate privacy or security..." (direct reply, no Vertex AI call)
```

#### Example 3: Clear Request → PASS_THROUGH
```
User: "Analyze this photo and identify the architectural style"

Streaming Response:
1. "OK" (immediate, <10ms)
2. "Processing your request..." (after analysis, ~500ms)
3. [AI analysis of the photo] (vertex AI response with original prompt)
```

### 5. **Performance Optimizations**

#### Fast Analysis Configuration
```python
# api/config.py additions

class Settings(BaseSettings):
    # ... existing settings
    
    # Background analysis optimizations
    background_analysis_timeout: float = 2.0  # Max 2 seconds for analysis
    fast_analysis_enabled: bool = True  # Use simplified prompts
    immediate_response_enabled: bool = True  # Send "OK" immediately
    
    # Status message customization
    status_messages: Dict[str, str] = {
        "refine": "I am generating an enhanced response based on your request...",
        "direct_reply": "Let me help you with that directly...",
        "pass_through": "Processing your request...",
        "immediate": "OK"
    }
```

#### Gemini-Flash Optimization Settings
```python
# Faster analysis configuration
FAST_GENERATION_CONFIG = {
    "temperature": 0.1,        # More predictable
    "maxOutputTokens": 200,    # Smaller responses
    "topP": 0.8,              # Focused sampling
    "topK": 20                # Reduced options
}

BACKGROUND_TIMEOUT = 1.5  # Aggressive timeout for HTTP calls
```

## Benefits of Optimized Streaming

### 1. **Immediate User Feedback**
- User sees response within 10ms
- No perceived delay regardless of analysis time
- Maintains engagement during processing

### 2. **Transparent Intelligence**
- Users don't know about interception happening
- Smooth streaming experience throughout
- Natural conversation flow maintained

### 3. **Performance Optimized**
- Background analysis with 2-second max timeout
- Simplified prompts for faster Gemini-Flash responses
- Fallback to pass-through if analysis is slow

### 4. **Fault Tolerant**
- Analysis failures don't block user experience
- Graceful degradation to original functionality
- Timeout protection prevents hanging requests

### 5. **Cost Efficient**
- Still prevents unnecessary Vertex AI calls for direct replies
- Only adds small Gemini-Flash calls for analysis
- Optimized generation configs reduce token usage

This optimized design provides the best of both worlds: **immediate responsiveness** for great UX and **intelligent processing** for better results, all while maintaining the streaming nature of your V2 API.