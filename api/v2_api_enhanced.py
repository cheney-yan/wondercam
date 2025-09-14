"""
Enhanced V2 API Endpoints with Intelligent Prompt Analysis
Optimized streaming with immediate response and background analysis
"""

import asyncio
import json
import logging
import time
import sys
from typing import AsyncGenerator, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

from v2_models import V2ChatRequest, V2ResponseChunk, V2ErrorResponse
from v2_translator import V2MessageTranslator
from auth_handler import AuthenticationHandler
from supabase_auth import verify_token
from config import settings
from vertex_formatter import VertexAIResponseFormatter, get_enhanced_status_message
from prompt_analyzer import AnalysisAction, AnalysisResult, get_prompt_analyzer

logger = logging.getLogger(__name__)

# Create router for enhanced v2 API
v2_enhanced_router = APIRouter(prefix="/v2", tags=["v2-enhanced"])
security = HTTPBearer()

# Initialize components
auth_handler = AuthenticationHandler(
    credentials_path=settings.google_application_credentials
)

translator = None
formatter = VertexAIResponseFormatter()

def get_translator() -> V2MessageTranslator:
    """Get or initialize translator"""
    global translator
    if not translator:
        project_id = auth_handler.get_project_id()
        translator = V2MessageTranslator(project_id=project_id)
    return translator

async def run_background_analysis(request: V2ChatRequest, current_translator: V2MessageTranslator) -> AnalysisResult:
    """Run background prompt analysis"""
    
    # Extract text content
    text_parts = [part.text for part in request.contents if part.text and part.text.strip()]
    image_parts = [part for part in request.contents if part.inlineData and 
                  part.inlineData.get("mimeType", "").startswith("image/")]
    
    if not text_parts:
        return AnalysisResult(
            action=AnalysisAction.PASS_THROUGH,
            reasoning="No text content to analyze"
        )
    
    combined_text = " ".join(text_parts).strip()
    has_images = len(image_parts) > 0
    
    logger.info(f"🔍 Background analysis: '{combined_text[:100]}...' (has_images: {has_images})")
    
    # Get prompt analyzer
    analyzer = get_prompt_analyzer()
    if not analyzer:
        return AnalysisResult(
            action=AnalysisAction.PASS_THROUGH,
            reasoning="Prompt analyzer not available"
        )
    
    # Run analysis
    try:
        result = await analyzer.analyze_prompt(
            combined_text,
            has_images,
            timeout_seconds=settings.prompt_analysis_timeout
        )
        
        return AnalysisResult(
            action=result.action,
            refined_prompt=result.refined_prompt,
            direct_reply=result.direct_reply,
            confidence=result.confidence,
            reasoning=result.reasoning
        )
        
    except Exception as e:
        logger.error(f"❌ Background analysis error: {e}")
        return AnalysisResult(
            action=AnalysisAction.PASS_THROUGH,
            reasoning=f"Analysis failed: {str(e)}"
        )

def apply_refined_prompt(request: V2ChatRequest, refined_prompt: str):
    """Apply refined prompt to request"""
    for i, part in enumerate(request.contents):
        if part.text and part.text.strip():
            original_text = part.text
            part.text = refined_prompt
            logger.info(f"🔄 Applied refinement: '{original_text[:50]}...' → '{refined_prompt[:50]}...'")
            break

async def stream_from_vertex_ai(vertex_request: Any, current_translator: V2MessageTranslator) -> AsyncGenerator[str, None]:
    """Stream response from Vertex AI"""
    
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
            
            # Format error as Vertex AI response
            error_message = "I encountered an issue processing your request. Please try again."
            yield formatter.format_error_response(error_message)
            return
        
        # Stream Vertex AI response directly - already in correct format
        logger.info("🚀 Streaming Vertex AI response directly...")
        async for chunk in response.aiter_text():
            # Vertex AI chunks are already in the correct format
            yield chunk

async def stream_v2_enhanced_response_with_flush(request: V2ChatRequest, user: dict) -> AsyncGenerator[bytes, None]:
    """Enhanced streaming V2 API with forced network flushing"""
    
    try:
        # Step 1: IMMEDIATE "OK" confirmation
        logger.info("✅ Sending immediate OK acknowledgment...")
        ok_response = formatter.format_immediate_response()
        yield ok_response.encode('utf-8')
        logger.info("🚀 OK message yielded")

        # Step 2: Initialize translator and authentication AFTER OK message
        logger.info("🔧 Initializing translator and authentication...")
        current_translator = get_translator()
        
        # Step 3: Background analysis (completely skip if disabled)
        analysis_result = AnalysisResult(
            action=AnalysisAction.PASS_THROUGH,
            reasoning="Using pass-through for immediate response"
        )
        
        # Only do analysis if enabled
        if settings.prompt_analysis_enabled:
            logger.info("🧠 Starting background prompt analysis...")
            try:
                # Start analysis task but don't wait for it
                analysis_task = asyncio.create_task(
                    run_background_analysis(request, current_translator)
                )
                
                # Try to get quick analysis result (very short timeout for responsiveness)
                analysis_result = await asyncio.wait_for(analysis_task, timeout=0.1)
                logger.info(f"✅ Quick analysis completed: {analysis_result.action}")
                
            except asyncio.TimeoutError:
                logger.info("⏰ Analysis taking too long, proceeding with pass-through for responsiveness")
                # Cancel the analysis task to free resources
                analysis_task.cancel()
                
            except Exception as e:
                logger.warning(f"⚠️ Analysis error, proceeding with pass-through: {e}")
        else:
            logger.info("🔄 Analysis disabled, using pass-through")
        
        # Step 4: Handle analysis result quickly
        if analysis_result.action == AnalysisAction.DIRECT_REPLY:
            # Stream direct reply as final response
            logger.info("🛑 Streaming direct reply")
            direct_response = formatter.format_direct_reply(analysis_result.direct_reply)
            yield direct_response.encode('utf-8')
            return
        
        # Step 5: Apply refined prompt if needed (minimal processing)
        if analysis_result.action == AnalysisAction.REFINE and analysis_result.refined_prompt:
            logger.info("✨ Applying refined prompt")
            apply_refined_prompt(request, analysis_result.refined_prompt)
        
        # Step 6: Stream from Vertex AI
        logger.info("🎯 Starting Vertex AI streaming...")
        vertex_request = current_translator.v2_to_vertex(request)
        
        async for vertex_chunk in stream_from_vertex_ai(vertex_request, current_translator):
            yield vertex_chunk.encode('utf-8')
        
        logger.info("✅ Enhanced streaming completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Enhanced streaming error: {e}")
        error_message = f"I apologize, but I encountered an error processing your request.\n\nPlease try again."
        error_response = formatter.format_error_response(error_message)
        yield error_response.encode('utf-8')

async def stream_v2_enhanced_response(request: V2ChatRequest, user: dict) -> AsyncGenerator[str, None]:
    """Enhanced streaming V2 API with immediate response and background analysis"""
    
    try:
        # Step 1: IMMEDIATE "OK" confirmation - send this FIRST before any blocking operations
        logger.info("✅ Sending immediate OK acknowledgment...")
        ok_response = formatter.format_immediate_response()
        yield ok_response

        # Step 2: Initialize translator and authentication AFTER OK message
        logger.info("🔧 Initializing translator and authentication...")
        current_translator = get_translator()
        
        # Step 3: Background analysis (completely skip if disabled)
        analysis_result = AnalysisResult(
            action=AnalysisAction.PASS_THROUGH,
            reasoning="Using pass-through for immediate response"
        )
        
        # Only do analysis if enabled
        if settings.prompt_analysis_enabled:
            logger.info("🧠 Starting background prompt analysis...")
            try:
                # Start analysis task but don't wait for it
                analysis_task = asyncio.create_task(
                    run_background_analysis(request, current_translator)
                )
                
                # Try to get quick analysis result (very short timeout for responsiveness)
                analysis_result = await asyncio.wait_for(analysis_task, timeout=0.1)
                logger.info(f"✅ Quick analysis completed: {analysis_result.action}")
                
            except asyncio.TimeoutError:
                logger.info("⏰ Analysis taking too long, proceeding with pass-through for responsiveness")
                # Cancel the analysis task to free resources
                analysis_task.cancel()
                
            except Exception as e:
                logger.warning(f"⚠️ Analysis error, proceeding with pass-through: {e}")
        else:
            logger.info("🔄 Analysis disabled, using pass-through")
        
        # Step 4: Handle analysis result quickly
        if analysis_result.action == AnalysisAction.DIRECT_REPLY:
            # Stream direct reply as final response
            logger.info("🛑 Streaming direct reply")
            yield formatter.format_direct_reply(analysis_result.direct_reply)
            return
        
        # Step 5: Apply refined prompt if needed (minimal processing)
        if analysis_result.action == AnalysisAction.REFINE and analysis_result.refined_prompt:
            logger.info("✨ Applying refined prompt")
            apply_refined_prompt(request, analysis_result.refined_prompt)
        
        # Step 6: Stream from Vertex AI
        logger.info("🎯 Starting Vertex AI streaming...")
        vertex_request = current_translator.v2_to_vertex(request)
        
        async for vertex_chunk in stream_from_vertex_ai(vertex_request, current_translator):
            yield vertex_chunk
        
        logger.info("✅ Enhanced streaming completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Enhanced streaming error: {e}")
        error_message = f"I apologize, but I encountered an error processing your request.\n\nPlease try again."
        yield formatter.format_error_response(error_message)

@v2_enhanced_router.post("/echat")
async def v2_enhanced_chat_endpoint(
    request: V2ChatRequest,
    user: dict = Depends(verify_token)
):
    """
    Enhanced V2 Chat endpoint with intelligent prompt analysis
    Features immediate response, background analysis, and optimized streaming
    """
    
    # Get user ID safely from Supabase user object
    user_id = getattr(user, 'id', 'unknown') if user else 'unknown'
    
    logger.info(f"🚀 Enhanced V2 chat request from user {user_id} with {len(request.contents)} content parts")
    logger.info(f"📋 Request details: language={request.language}, stream={request.stream}")
    
    # Log content types for debugging
    text_parts = [part for part in request.contents if part.text]
    image_parts = [part for part in request.contents if part.inlineData and part.inlineData.get("mimeType", "").startswith("image/")]
    audio_parts = [part for part in request.contents if part.inlineData and part.inlineData.get("mimeType", "").startswith("audio/")]
    
    logger.info(f"📝 Content summary: {len(text_parts)} text, {len(image_parts)} images, {len(audio_parts)} audio")
    logger.info(f"🧠 Intelligent analysis: {'enabled' if settings.prompt_analysis_enabled else 'disabled'}")
    
    if not request.stream:
        # Non-streaming response (future implementation)
        raise HTTPException(status_code=501, detail="Non-streaming responses not yet implemented")
    
    # Use the flushing version for immediate OK delivery
    return StreamingResponse(
        stream_v2_enhanced_response_with_flush(request, user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

@v2_enhanced_router.get("/ehealth")
async def v2_enhanced_health_check():
    """Enhanced V2 API health check"""
    analyzer_status = "available" if get_prompt_analyzer() else "unavailable"
    
    return {
        "status": "healthy",
        "version": "v2-enhanced",
        "features": [
            "text", "image", "voice", "streaming", 
            "intelligent_analysis", "immediate_response", 
            "background_processing", "optimized_format"
        ],
        "intelligent_analysis": {
            "enabled": settings.prompt_analysis_enabled,
            "analyzer_status": analyzer_status,
            "timeout": settings.prompt_analysis_timeout,
            "model": settings.prompt_analysis_model
        },
        "optimizations": {
            "simplified_format": settings.use_simplified_format,
            "message_separation": settings.add_message_separation,
            "immediate_response": settings.immediate_response_text
        }
    }

@v2_enhanced_router.get("/ecapabilities")
async def v2_enhanced_capabilities():
    """Enhanced V2 API capabilities"""
    logger.info("📋 Enhanced V2 capabilities requested")
    
    return {
        "version": "v2-enhanced",
        "message_types": ["text", "image", "voice"],
        "languages": ["en", "zh", "es", "fr", "ja"],
        "features": {
            "streaming": True,
            "preprocessing": True,
            "intelligent_analysis": settings.prompt_analysis_enabled,
            "immediate_response": True,
            "background_processing": True,
            "prompt_refinement": True,
            "direct_replies": True,
            "optimized_format": settings.use_simplified_format,
            "image_generation": True,
            "image_analysis": True,
            "voice_processing": False,  # Future implementation
            "multi_modal": True
        },
        "analysis_actions": ["refine", "direct_reply", "pass_through"],
        "limits": {
            "max_messages": 100,
            "max_image_size": "10MB",
            "analysis_timeout": f"{settings.prompt_analysis_timeout}s",
            "supported_image_formats": ["jpeg", "png", "webp"],
            "supported_audio_formats": ["webm", "mp3", "wav"]  # Future
        }
    }

@v2_enhanced_router.get("/edebug")
async def v2_enhanced_debug_info():
    """Enhanced V2 API debug information"""
    logger.info("🔧 Enhanced V2 debug info requested")
    
    try:
        project_id = auth_handler.get_project_id()
        current_translator = get_translator()
        endpoint = current_translator.get_vertex_endpoint()
        analyzer = get_prompt_analyzer()
        
        return {
            "status": "healthy",
            "version": "v2-enhanced",
            "project_id": project_id,
            "vertex_endpoint": endpoint,
            "vertex_ai_location": settings.vertex_ai_location,
            "intelligent_analysis": {
                "enabled": settings.prompt_analysis_enabled,
                "analyzer_available": analyzer is not None,
                "timeout": settings.prompt_analysis_timeout,
                "model": settings.prompt_analysis_model
            },
            "response_optimization": {
                "simplified_format": settings.use_simplified_format,
                "message_separation": settings.add_message_separation,
                "immediate_response": settings.immediate_response_text
            },
            "debug_features": [
                "intelligent_preprocessing",
                "background_analysis", 
                "immediate_response",
                "optimized_streaming",
                "simplified_vertex_format",
                "enhanced_message_formatting"
            ],
            "streaming_architecture": {
                "immediate_acknowledgment": True,
                "background_analysis": True,
                "parallel_processing": True,
                "timeout_protection": True,
                "vertex_ai_compatibility": True
            }
        }
    except Exception as e:
        logger.error(f"❌ Enhanced V2 debug info failed: {e}")
        return {
            "status": "error",
            "version": "v2-enhanced",
            "error": str(e),
            "intelligent_analysis": {
                "enabled": settings.prompt_analysis_enabled,
                "error": "Debug info generation failed"
            }
        }
