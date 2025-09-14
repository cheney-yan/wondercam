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
    """Stream V2 API response - direct proxy to Vertex AI without processing"""
    
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
            
            response = await client.post(
                f"{vertex_endpoint}?alt=sse",
                headers=headers,
                json=vertex_request.model_dump()
            )
            
            logger.info(f"📥 Vertex AI response status: {response.status_code}")
            
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
            
            # Step 4: Stream chunks immediately without any processing
            logger.info("🚀 Direct streaming - yielding chunks ASAP...")
            async for chunk in response.aiter_text():
                yield chunk
        
        logger.info("✅ Direct streaming completed")
        
    except Exception as e:
        logger.error(f"V2 API streaming error: {e}")
        error_chunk = V2ResponseChunk(
            type="error",
            content=f"Internal error: {str(e)}",
            is_final=True
        )
        yield f"data: {json.dumps(error_chunk.model_dump())}\n\n"

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
            "direct_proxy": True,  # Direct streaming proxy without response processing
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
            "proxy_mode": "direct_streaming",
            "debug_features": [
                "request_preprocessing",
                "vertex_ai_integration",
                "direct_proxy_streaming",
                "minimal_processing"
            ],
            "streaming_optimizations": {
                "direct_pass_through": True,
                "no_response_processing": True,
                "minimal_overhead": True,
                "maximum_speed": True
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
