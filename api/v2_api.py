"""
V2 API Endpoints for WonderCam
Simplified, extensible API with streaming support and preprocessing
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import json
import logging
from typing import AsyncGenerator

from v2_models import V2ChatRequest, V2ResponseChunk, V2ErrorResponse
from v2_translator import V2MessageTranslator
from auth_handler import AuthenticationHandler
from supabase_auth import verify_token
from config import settings

logger = logging.getLogger(__name__)

# Create router for v2 API
v2_router = APIRouter(prefix="/v2", tags=["v2"])
security = HTTPBearer()

# Initialize components
auth_handler = AuthenticationHandler(
    credentials_path=settings.google_application_credentials
)

translator = None

def get_translator() -> V2MessageTranslator:
    """Get or initialize translator"""
    global translator
    if not translator:
        project_id = auth_handler.get_project_id()
        translator = V2MessageTranslator(project_id=project_id)
    return translator

async def stream_v2_response(request: V2ChatRequest, user: dict) -> AsyncGenerator[str, None]:
    """Stream V2 API response with preprocessing and Vertex AI integration"""
    
    try:
        current_translator = get_translator()
        
        # Step 1: Preprocessing - can yield system messages
        logger.info("Starting V2 preprocessing...")
        async for preprocess_chunk in current_translator.preprocess_request(request):
            chunk_json = json.dumps(preprocess_chunk.model_dump())
            yield f"data: {chunk_json}\n\n"
        
        # Step 2: Convert to Vertex AI format
        logger.info("Converting V2 request to Vertex AI format...")
        vertex_request = current_translator.v2_to_vertex(request)
        
        # Step 3: Call Vertex AI
        logger.info("Calling Vertex AI...")
        vertex_endpoint = current_translator.get_vertex_endpoint()
        access_token = auth_handler.get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info(f"🔗 Calling Vertex AI endpoint: {vertex_endpoint}?alt=sse")
            logger.info(f"📤 Vertex AI request parts: {len(vertex_request.contents[0].parts if vertex_request.contents else [])}")
            
            response = await client.post(
                f"{vertex_endpoint}?alt=sse",
                headers=headers,
                json=vertex_request.model_dump()
            )
            
            logger.info(f"📥 Vertex AI response status: {response.status_code}")
            logger.info(f"📋 Vertex AI response headers: {dict(response.headers)}")
            
            if not response.is_success:
                error_text = response.text
                logger.error(f"❌ Vertex AI error: {response.status_code} - {error_text}")
                logger.error(f"🔍 Request that failed: {json.dumps(vertex_request.model_dump(), indent=2)}")
                
                error_chunk = V2ResponseChunk(
                    type="error",
                    content=f"AI service error: {error_text}",
                    is_final=True
                )
                yield f"data: {json.dumps(error_chunk.model_dump())}\n\n"
                return
        
        # Step 4: Stream Vertex AI response through V2 format with interception
        logger.info("🌊 Streaming Vertex AI response with interception capabilities...")
        vertex_stream = stream_vertex_response(response)
        
        # Configure stream interception based on request or settings
        intercept_config = {
            "filter_content": request.preprocessing and request.preprocessing.get("filter_content", False),
            "modify_responses": request.preprocessing and request.preprocessing.get("modify_responses", False), 
            "inject_system_messages": request.preprocessing and request.preprocessing.get("inject_system", False),
        }
        
        # Override with default safe settings if no config provided
        if not any(intercept_config.values()):
            intercept_config = {
                "filter_content": True,      # Enable basic content filtering by default
                "modify_responses": False,    # Disable response modification by default
                "inject_system_messages": False,  # Disable system injection by default
            }
        
        logger.info(f"🛡️ Stream interception enabled: {intercept_config}")
        
        chunk_count = 0
        async for v2_chunk in current_translator.vertex_to_v2_stream(vertex_stream, intercept_config):
            chunk_count += 1
            chunk_json = json.dumps(v2_chunk.model_dump())
            logger.debug(f"📦 Chunk {chunk_count}: {v2_chunk.type} - {len(str(v2_chunk.content))} chars")
            yield f"data: {chunk_json}\n\n"
        
        logger.info(f"✅ Streaming completed: {chunk_count} chunks sent with interception")
        # Send completion signal
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"V2 API streaming error: {e}")
        error_chunk = V2ResponseChunk(
            type="error", 
            content=f"Internal error: {str(e)}",
            is_final=True
        )
        yield f"data: {json.dumps(error_chunk.model_dump())}\n\n"

async def stream_vertex_response(response: httpx.Response) -> AsyncGenerator:
    """Stream response from Vertex AI with detailed logging"""
    
    buffer = ""
    line_count = 0
    valid_chunks = 0
    
    logger.info("📡 Starting to process Vertex AI stream...")
    
    async for chunk in response.aiter_text():
        buffer += chunk
        lines = buffer.split('\n')
        buffer = lines.pop()
        
        for line in lines:
            line_count += 1
            if line.startswith('data:'):
                try:
                    json_str = line[5:].strip()
                    if json_str and json_str != '[DONE]':
                        data = json.loads(json_str)
                        logger.debug(f"🔍 Raw Vertex AI data: {json.dumps(data, indent=2)}")
                        
                        # Extract text content
                        if data.get('candidates') and data['candidates'][0].get('content', {}).get('parts'):
                            for part in data['candidates'][0]['content']['parts']:
                                if part.get('text'):
                                    valid_chunks += 1
                                    logger.debug(f"📝 Text chunk {valid_chunks}: {part['text'][:100]}...")
                                    yield part['text']
                                elif part.get('inlineData', {}).get('data'):
                                    valid_chunks += 1
                                    logger.debug(f"🖼️ Image chunk {valid_chunks}: {len(part['inlineData']['data'])} bytes")
                                    yield {
                                        "type": "image",
                                        "data": part['inlineData']['data']
                                    }
                        else:
                            logger.warning(f"⚠️ Vertex AI chunk has no content parts: {json.dumps(data)}")
                    elif json_str == '[DONE]':
                        logger.info("🏁 Vertex AI stream completed with [DONE] signal")
                except json.JSONDecodeError as e:
                    logger.warning(f"❌ Failed to parse Vertex AI response line {line_count}: {line[:100]} - {e}")
            elif line.strip():
                logger.debug(f"ℹ️ Non-data line {line_count}: {line[:100]}")
    
    logger.info(f"📊 Vertex AI stream summary: {line_count} lines processed, {valid_chunks} valid content chunks extracted")

@v2_router.post("/chat")
async def v2_chat_endpoint(
    request: V2ChatRequest,
    user: dict = Depends(verify_token)
):
    """
    V2 Chat endpoint with streaming support
    Supports text, image, and voice messages with preprocessing
    """
    
    # Get user ID safely from Supabase user object
    user_id = getattr(user, 'id', 'unknown') if user else 'unknown'
    
    logger.info(f"🚀 V2 chat request from user {user_id} with {len(request.contents)} content parts")
    logger.info(f"📋 Request details: language={request.language}, stream={request.stream}")
    
    # Log content types for debugging
    text_parts = [part for part in request.contents if part.text]
    image_parts = [part for part in request.contents if part.inlineData and part.inlineData.get("mimeType", "").startswith("image/")]
    audio_parts = [part for part in request.contents if part.inlineData and part.inlineData.get("mimeType", "").startswith("audio/")]
    
    logger.info(f"📝 Content summary: {len(text_parts)} text, {len(image_parts)} images, {len(audio_parts)} audio")
    logger.info(f"🔍 Processing user-only content - no conversation history needed")
    
    if not request.stream:
        # Non-streaming response (future implementation)
        raise HTTPException(status_code=501, detail="Non-streaming responses not yet implemented")
    
    return StreamingResponse(
        stream_v2_response(request, user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@v2_router.get("/health")
async def v2_health_check():
    """V2 API health check"""
    return {
        "status": "healthy",
        "version": "v2",
        "features": ["text", "image", "voice", "streaming", "preprocessing"]
    }

@v2_router.get("/capabilities")
async def v2_capabilities():
    """V2 API capabilities"""
    logger.info("📋 V2 capabilities requested")
    return {
        "version": "v2",
        "message_types": ["text", "image", "voice"],
        "languages": ["en", "zh", "es", "fr", "ja"],
        "features": {
            "streaming": True,
            "preprocessing": True,
            "image_generation": True,
            "image_analysis": True,
            "voice_processing": False,  # Future implementation
            "multi_modal": True
        },
        "limits": {
            "max_messages": 100,
            "max_image_size": "10MB",
            "supported_image_formats": ["jpeg", "png", "webp"],
            "supported_audio_formats": ["webm", "mp3", "wav"]  # Future
        }
    }

@v2_router.get("/debug")
async def v2_debug_info():
    """V2 API debug information"""
    logger.info("🔧 V2 debug info requested")
    try:
        auth_handler = AuthenticationHandler(
            credentials_path=settings.google_application_credentials
        )
        project_id = auth_handler.get_project_id()
        
        translator = V2MessageTranslator(project_id=project_id)
        endpoint = translator.get_vertex_endpoint()
        
        return {
            "status": "healthy",
            "version": "v2",
            "project_id": project_id,
            "vertex_endpoint": endpoint,
            "vertex_ai_location": settings.vertex_ai_location,
            "logging_enabled": True,
            "debug_features": [
                "comprehensive_logging",
                "vertex_ai_response_tracking", 
                "content_validation",
                "stream_monitoring",
                "stream_interception",
                "configurable_regions"
            ],
            "interception_capabilities": {
                "content_filtering": True,
                "response_modification": True,
                "system_message_injection": True,
                "image_filtering": True,
                "custom_interceptors": True
            }
        }
    except Exception as e:
        logger.error(f"❌ V2 debug info failed: {e}")
        return {
            "status": "error",
            "version": "v2",
            "error": str(e),
            "logging_enabled": True
        }

@v2_router.post("/chat/test-interception")
async def test_stream_interception(
    user: dict = Depends(verify_token)
):
    """Test endpoint for stream interception capabilities"""
    
    user_id = getattr(user, 'id', 'unknown') if user else 'unknown'
    logger.info(f"🧪 Testing stream interception for user {user_id}")
    
    # Create a test request with interception enabled
    from v2_models import V2ContentPart
    test_request = V2ChatRequest(
        contents=[
            V2ContentPart(text="I need help with understanding passwords and security vulnerabilities. Can you explain the best practices?")
        ],
        language="en",
        preprocessing={
            "filter_content": True,
            "modify_responses": True,
            "inject_system": True
        }
    )
    
    return StreamingResponse(
        stream_v2_response(test_request, user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Interception-Test": "enabled"
        }
    )