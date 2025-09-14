"""
V2 API Message Translator
Converts between V2 API format and Vertex AI format with extensible processing
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from v2_models import (
    V2Message, V2ChatRequest, V2ChatRequestLegacy, V2ResponseChunk, MessageType,
    V2MessageContentSimple, VertexContent, VertexRequest, V2SystemMessage, V2ContentPart
)
from config import settings
import logging
import base64
import json
import time

logger = logging.getLogger(__name__)

class V2MessageTranslator:
    """Translates between V2 API format and Vertex AI format"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.language_instructions = {
            'en': 'Respond in English.',
            'zh': '请用中文回答。',
            'es': 'Responde en español.',
            'fr': 'Répondez en français.',
            'ja': '日本語で答えてください。'
        }
        
        # Initialize prompt analyzer if enabled
        self.prompt_analyzer = None
        if settings.prompt_analysis_enabled:
            try:
                from prompt_analyzer import get_prompt_analyzer
                self.prompt_analyzer = get_prompt_analyzer()
                if self.prompt_analyzer:
                    logger.info("✅ Prompt analyzer initialized in translator")
                else:
                    logger.warning("⚠️ Prompt analyzer failed to initialize")
            except ImportError as e:
                logger.warning(f"⚠️ Prompt analyzer not available: {e}")
            except Exception as e:
                logger.error(f"❌ Error initializing prompt analyzer: {e}")
    
    def validate_user_content(self, request: V2ChatRequest) -> Dict[str, Any]:
        """
        Validate that all user content parts can be processed
        Returns validation summary and any issues
        """
        validation = {
            "valid": True,
            "issues": [],
            "summary": {
                "text_parts": 0,
                "image_parts": 0,
                "audio_parts": 0,
                "unknown_parts": 0
            }
        }
        
        for i, part in enumerate(request.contents):
            if part.text:
                validation["summary"]["text_parts"] += 1
                if len(part.text.strip()) == 0:
                    validation["issues"].append(f"Content part {i}: Empty text content")
                    
            elif part.inlineData:
                mime_type = part.inlineData.get("mimeType", "")
                data = part.inlineData.get("data", "")
                
                if mime_type.startswith("image/"):
                    validation["summary"]["image_parts"] += 1
                    if not data:
                        validation["issues"].append(f"Content part {i}: Empty image data")
                elif mime_type.startswith("audio/"):
                    validation["summary"]["audio_parts"] += 1
                    if not data:
                        validation["issues"].append(f"Content part {i}: Empty audio data")
                else:
                    validation["summary"]["unknown_parts"] += 1
                    validation["issues"].append(f"Content part {i}: Unknown mime type '{mime_type}'")
            else:
                validation["issues"].append(f"Content part {i}: Neither text nor inlineData provided")
        
        if validation["issues"]:
            validation["valid"] = False
            
        return validation

    async def preprocess_request(self, request: V2ChatRequest) -> AsyncGenerator[V2ResponseChunk, None]:
        """
        Enhanced preprocessing with intelligent prompt analysis
        Validates user content and performs smart prompt analysis for better responses
        """
        logger.info(f"🧠 Starting intelligent preprocessing for {len(request.contents)} content parts")
        
        # Step 1: Validate all content parts
        validation = self.validate_user_content(request)
        logger.info(f"Content validation: {validation['summary']}")
        
        if not validation["valid"]:
            logger.warning(f"Content validation issues: {validation['issues']}")
            yield V2ResponseChunk(
                type="system",
                content=V2SystemMessage(
                    type="validation_warning",
                    content=f"Some content parts have issues: {', '.join(validation['issues'][:3])}...",
                ).model_dump()
            )
        
        # Step 2: Extract text content for analysis
        text_parts = [part.text for part in request.contents if part.text and part.text.strip()]
        image_parts = [part for part in request.contents if part.inlineData and
                      part.inlineData.get("mimeType", "").startswith("image/")]
        
        # Step 3: Perform intelligent analysis if enabled and text content exists
        if (hasattr(self, 'prompt_analyzer') and self.prompt_analyzer and
            text_parts and
            settings.prompt_analysis_enabled and
            len(" ".join(text_parts).strip()) > 0):
            
            combined_text = " ".join(text_parts).strip()
            has_images = len(image_parts) > 0
            
            logger.info(f"🔍 Analyzing message: '{combined_text[:100]}...' (has_images: {has_images})")
            
            start_time = time.time()
            
            try:
                from prompt_analyzer import AnalysisAction
                
                # Run intelligent analysis
                analysis_result = await self.prompt_analyzer.analyze_prompt(
                    combined_text,
                    has_images,
                    timeout_seconds=settings.prompt_analysis_timeout
                )
                
                analysis_time = int((time.time() - start_time) * 1000)
                logger.info(f"✅ Analysis completed in {analysis_time}ms: {analysis_result.action} (confidence: {analysis_result.confidence})")
                
                # Handle analysis results
                if analysis_result.action == AnalysisAction.DIRECT_REPLY:
                    # Stop processing and reply directly
                    logger.info("🛑 Analysis suggests direct reply - stopping preprocessing")
                    request._stop_processing = True
                    request._direct_reply = analysis_result.direct_reply
                    return
                    
                elif analysis_result.action == AnalysisAction.REFINED:
                    # Apply refined prompt
                    logger.info("✨ Analysis suggests refinement - updating request")
                    if analysis_result.refined_prompt:
                        # Replace or enhance the first text part with refined prompt
                        for i, part in enumerate(request.contents):
                            if part.text and part.text.strip():
                                original_text = part.text
                                part.text = analysis_result.refined_prompt
                                logger.info(f"🔄 Refined prompt: '{original_text[:50]}...' → '{part.text[:50]}...'")
                                break
                        request._analysis_applied = True
                        request._original_prompt = combined_text
                        request._refined_prompt = analysis_result.refined_prompt
                
                # Log analysis decision
                request._analysis_result = analysis_result
                
            except Exception as e:
                logger.error(f"❌ Intelligent analysis error: {e}")
                # Continue with original logic on error
        
        # Step 4: Legacy preprocessing logic (image generation, analysis detection)
        if text_parts:
            combined_text = " ".join(text_parts).lower()
            
            # Custom preprocessing logic examples
            if "generate" in combined_text and "image" in combined_text:
                yield V2ResponseChunk(
                    type="system",
                    content=V2SystemMessage(
                        type="preprocessing",
                        content="I'll generate an image for you. This will consume 2 credits.",
                        action="confirm_generation"
                    ).model_dump()
                )
            
            if "analyze" in combined_text and image_parts:
                yield V2ResponseChunk(
                    type="system",
                    content=V2SystemMessage(
                        type="preprocessing",
                        content="I'll analyze your image. This will consume 1 credit.",
                        action="confirm_analysis"
                    ).model_dump()
                )
    
    def v2_to_vertex(self, request: V2ChatRequest) -> VertexRequest:
        """
        Convert V2 user content to Vertex AI conversation format
        
        Note: V2 API only provides user content parts. This method:
        1. Validates all content parts can be processed
        2. Creates proper Vertex AI conversation structure 
        3. Adds language instructions as needed
        4. Formats as single user message to Vertex AI
        """
        
        # Validate content before processing
        validation = self.validate_user_content(request)
        if not validation["valid"]:
            logger.warning(f"Processing request with validation issues: {validation['issues']}")
        
        parts = []
        
        # Add language instruction if specified (prepended to user content)
        if request.language and request.language != "en":
            lang_instruction = self.language_instructions.get(request.language, "")
            if lang_instruction:
                parts.append({"text": lang_instruction})
                logger.info(f"Added language instruction for {request.language}")
        
        # Process all user content parts in order
        processed_parts = {"text": 0, "image": 0, "audio": 0, "unknown": 0}
        
        for i, content_part in enumerate(request.contents):
            if content_part.text:
                # Handle text content
                text_content = content_part.text.strip()
                if text_content:  # Skip empty text
                    parts.append({"text": text_content})
                    processed_parts["text"] += 1
                else:
                    logger.warning(f"Skipping empty text content at index {i}")
            
            elif content_part.inlineData:
                # Handle inline data (images, audio)
                inline_data = content_part.inlineData
                mime_type = inline_data.get("mimeType", "image/jpeg")
                data = inline_data.get("data", "")
                
                if not data:
                    logger.warning(f"Skipping empty inline data at index {i}")
                    continue
                
                # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
                if "," in data:
                    data = data.split(",")[1]
                
                if mime_type.startswith("image/"):
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": data
                        }
                    })
                    processed_parts["image"] += 1
                elif mime_type.startswith("audio/"):
                    # Audio content support
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": data
                        }
                    })
                    processed_parts["audio"] += 1
                else:
                    # Unknown mime type, convert to text placeholder
                    parts.append({"text": f"[Unsupported content type: {mime_type}]"})
                    processed_parts["unknown"] += 1
                    logger.warning(f"Unknown mime type '{mime_type}' at index {i}, converted to text placeholder")
            else:
                logger.warning(f"Skipping invalid content part at index {i} - no text or inlineData")
        
        logger.info(f"Processed content parts: {processed_parts}")
        
        # Create single user message for Vertex AI (all content is from user)
        contents = [VertexContent(role="user", parts=parts)]
        
        # Create Vertex AI request with optimized settings
        vertex_request = VertexRequest(
            contents=[c.model_dump() for c in contents],
            safetySettings=[
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
            ],
            tools=[],
            generationConfig={
                "temperature": 1,
                "topP": 1,
                "responseModalities": ["TEXT", "IMAGE"]
            }
        )
        
        return vertex_request
    
    async def vertex_to_v2_stream(
        self, 
        vertex_response_stream: AsyncGenerator,
        intercept_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[V2ResponseChunk, None]:
        """
        Convert Vertex AI streaming response to V2 API format with stream interception
        
        Args:
            vertex_response_stream: The Vertex AI response stream
            intercept_config: Configuration for stream interception and modification
                {
                    "filter_content": bool,           # Filter inappropriate content
                    "modify_responses": bool,         # Modify responses in real-time
                    "inject_system_messages": bool,  # Inject system messages
                    "content_filters": [str],         # List of content filters to apply
                    "response_modifiers": [str],      # List of response modifiers
                    "custom_interceptors": [callable] # Custom interception functions
                }
        """
        
        # Default interception config
        config = intercept_config or {}
        filter_content = config.get("filter_content", False)
        modify_responses = config.get("modify_responses", False)
        inject_system = config.get("inject_system_messages", False)
        
        stream_chunk_count = 0
        intercepted_chunks = 0
        modified_chunks = 0
        
        logger.info("🔄 Starting Vertex AI to V2 stream conversion with interception...")
        logger.info(f"🛡️ Interception config: filter={filter_content}, modify={modify_responses}, inject={inject_system}")
        
        # Buffer for accumulating partial responses if needed
        text_buffer = ""
        
        async for chunk in vertex_response_stream:
            stream_chunk_count += 1
            
            if isinstance(chunk, str):
                # Text chunk - apply interception
                text_buffer += chunk
                
                # Apply content filtering
                if filter_content:
                    filtered_chunk = await self._filter_content(chunk)
                    if filtered_chunk != chunk:
                        intercepted_chunks += 1
                        logger.debug(f"🛡️ Filtered chunk {stream_chunk_count}: content modified")
                        
                        if filtered_chunk is None:
                            # Content blocked completely
                            logger.warning(f"🚫 Blocked inappropriate content in chunk {stream_chunk_count}")
                            continue
                        chunk = filtered_chunk
                
                # Apply response modifications
                if modify_responses:
                    modified_chunk = await self._modify_response(chunk, text_buffer)
                    if modified_chunk != chunk:
                        modified_chunks += 1
                        logger.debug(f"✏️ Modified chunk {stream_chunk_count}: response enhanced")
                        chunk = modified_chunk
                
                # Check if we should inject system messages
                if inject_system and self._should_inject_system_message(text_buffer):
                    logger.debug(f"💬 Injecting system message before chunk {stream_chunk_count}")
                    yield V2ResponseChunk(
                        type="system",
                        content=V2SystemMessage(
                            type="stream_info",
                            content="The AI is analyzing your request. Response may be enhanced based on content filters.",
                        ).model_dump(),
                        is_final=False
                    )
                
                logger.debug(f"📝 Converting text chunk {stream_chunk_count}: {chunk[:50]}...")
                yield V2ResponseChunk(
                    type="text",
                    content=chunk,
                    is_final=False
                )
                
            elif isinstance(chunk, dict) and chunk.get("type") == "image":
                # Image chunk - apply image-specific interception
                image_data = chunk.get("data", "")
                
                if filter_content:
                    # Could add image content filtering here
                    filtered_image = await self._filter_image_content(image_data)
                    if filtered_image != image_data:
                        intercepted_chunks += 1
                        logger.debug(f"🖼️ Filtered image chunk {stream_chunk_count}")
                        image_data = filtered_image
                
                logger.debug(f"🖼️ Converting image chunk {stream_chunk_count}: {len(image_data)} bytes")
                yield V2ResponseChunk(
                    type="image",
                    content=image_data,
                    metadata={"mime_type": "image/png"},
                    is_final=False
                )
            else:
                # Handle other chunk types
                logger.warning(f"⚠️ Unknown chunk type {stream_chunk_count}: {type(chunk)} - {str(chunk)[:100]}")
        
        logger.info(f"🔄 Stream conversion completed: {stream_chunk_count} chunks processed")
        logger.info(f"🛡️ Interception summary: {intercepted_chunks} filtered, {modified_chunks} modified")
        
        # Send final chunk with interception summary
        final_content = ""
        if intercepted_chunks > 0 or modified_chunks > 0:
            final_content = f"[Stream processed: {intercepted_chunks} filtered, {modified_chunks} enhanced]"
        
        yield V2ResponseChunk(
            type="text",
            content=final_content,
            is_final=True
        )
    
    async def _filter_content(self, content: str) -> Optional[str]:
        """Filter inappropriate or unwanted content from text chunks"""
        
        # Example content filters
        inappropriate_patterns = [
            r'\b(hack|exploit|vulnerability)\b',  # Security-related
            r'\b(password|secret|token)\b',       # Sensitive data
        ]
        
        import re
        for pattern in inappropriate_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # Replace with placeholder or filter out
                content = re.sub(pattern, "[FILTERED]", content, flags=re.IGNORECASE)
                logger.debug(f"🛡️ Applied content filter: {pattern}")
        
        # Block entire chunk if too problematic
        if "[FILTERED]" in content and len(content.replace("[FILTERED]", "").strip()) < 5:
            return None  # Block completely
        
        return content
    
    async def _modify_response(self, chunk: str, full_context: str) -> str:
        """Modify response chunks to enhance or correct them"""
        
        # Example modifications
        modifications = {
            # Auto-correct common issues
            "your welcome": "you're welcome",
            "definately": "definitely",
            "seperate": "separate",
            
            # Enhance responses
            "I can help": "I'd be happy to help",
            "I don't know": "I'm not certain about that, but",
        }
        
        modified_chunk = chunk
        for original, replacement in modifications.items():
            if original.lower() in chunk.lower():
                modified_chunk = chunk.replace(original, replacement)
                logger.debug(f"✏️ Applied modification: '{original}' -> '{replacement}'")
        
        # Context-based modifications
        if "error" in full_context.lower() and "help" in chunk.lower():
            modified_chunk = chunk + " Let me provide some additional guidance."
            logger.debug("✏️ Added helpful context for error-related response")
        
        return modified_chunk
    
    async def _filter_image_content(self, image_data: str) -> str:
        """Filter image content (placeholder for future image analysis)"""
        # Future: Could integrate with image analysis APIs to detect inappropriate content
        logger.debug("🖼️ Image content filtering (placeholder)")
        return image_data
    
    def _should_inject_system_message(self, context: str) -> bool:
        """Determine if we should inject a system message based on context"""
        
        # Inject system messages for certain contexts
        trigger_phrases = [
            "I need help with",
            "Can you explain",
            "What is the best way",
        ]
        
        return any(phrase.lower() in context.lower() for phrase in trigger_phrases)
    
    def get_vertex_endpoint(self, model: str = "gemini-2.5-flash-image-preview") -> str:
        """Get Vertex AI endpoint URL using configured location"""
        location = settings.vertex_ai_location
        logger.info(f"🌍 Using Vertex AI location: {location} (from env: VERTEX_AI_LOCATION)")
        return f"https://aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{location}/publishers/google/models/{model}:streamGenerateContent"
    
    def detect_content_intent(self, request: V2ChatRequest) -> Dict[str, Any]:
        """Analyze content to detect user intent"""
        intents = {
            "image_generation": False,
            "image_analysis": False,
            "voice_processing": False,
            "general_chat": True
        }
        
        # Check text content for generation intent
        text_parts = [part.text for part in request.contents if part.text]
        if text_parts:
            combined_text = " ".join(text_parts).lower()
            if any(keyword in combined_text for keyword in ["generate", "create", "draw", "make an image"]):
                intents["image_generation"] = True
                intents["general_chat"] = False
        
        # Check for image analysis intent
        image_parts = [part for part in request.contents if part.inlineData and 
                      part.inlineData.get("mimeType", "").startswith("image/")]
        if image_parts:
            intents["image_analysis"] = True
            intents["general_chat"] = False
        
        # Check for voice processing
        audio_parts = [part for part in request.contents if part.inlineData and 
                      part.inlineData.get("mimeType", "").startswith("audio/")]
        if audio_parts:
            intents["voice_processing"] = True
            intents["general_chat"] = False
        
        return intents