# 🧠 Prompt Analysis Implementation - Code Examples

This document provides complete, ready-to-use code examples for implementing the intelligent prompt analysis system.

## Core Implementation Files

### 1. Complete `api/prompt_analyzer.py`

```python
"""
Intelligent Prompt Analysis Service using Gemini-Flash
Analyzes user prompts and decides whether to refine or reply directly
"""

from typing import Dict, Any, Optional, AsyncGenerator
from enum import Enum
import httpx
import json
import logging
from dataclasses import dataclass
import time
import asyncio
from datetime import datetime

from auth_handler import AuthenticationHandler
from config import settings

logger = logging.getLogger(__name__)

class AnalysisAction(str, Enum):
    """Possible actions from prompt analysis"""
    REFINE = "refine"           # Refine prompt and continue to Vertex AI
    DIRECT_REPLY = "direct_reply"  # Reply directly to user, stop processing
    PASS_THROUGH = "pass_through"  # Pass original prompt through unchanged

@dataclass
class PromptAnalysisResult:
    """Result of prompt analysis"""
    action: AnalysisAction
    refined_prompt: Optional[str] = None
    direct_reply: Optional[str] = None
    confidence: float = 0.0
    reasoning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[int] = None

class PromptAnalyzer:
    """Intelligent prompt analyzer using Gemini-Flash"""
    
    def __init__(self, project_id: str, auth_handler: AuthenticationHandler):
        self.project_id = project_id
        self.auth_handler = auth_handler
        self.analysis_prompts = self._load_analysis_prompts()
        self.stats = {
            "total_analyses": 0,
            "refine_count": 0,
            "direct_reply_count": 0,
            "pass_through_count": 0,
            "avg_processing_time_ms": 0
        }
    
    def _load_analysis_prompts(self) -> Dict[str, str]:
        """Load system prompts for different analysis types"""
        return {
            "main_analysis": """You are a smart prompt refinement AI for WonderCam, a photo analysis and creative AI assistant.

Analyze the user's message and decide ONE of these actions:

1. **REFINE**: If the message is unclear, too vague, or could benefit from enhancement
   - Examples: "help me", "what can you do", "analyze this", "make something"
   - Provide a refined, specific prompt that will get better AI results

2. **DIRECT_REPLY**: If the message is inappropriate, nonsensical, or should be declined
   - Examples: harmful requests, spam, gibberish, impossible tasks
   - Provide a polite but firm direct response

3. **PASS_THROUGH**: If the message is clear, specific, and appropriate as-is
   - Examples: "Analyze this photo and identify the architectural style", "Create a story about a robot"

User message: "{user_message}"

Respond in this EXACT JSON format:
{{
  "action": "refine|direct_reply|pass_through",
  "refined_prompt": "Enhanced specific prompt (only if action=refine)",
  "direct_reply": "Polite direct response (only if action=direct_reply)", 
  "confidence": 0.85,
  "reasoning": "Brief explanation of your decision"
}}

Important:
- Be helpful and constructive
- For REFINE, make prompts specific and actionable
- For DIRECT_REPLY, be polite but clear about limitations
- Only include refined_prompt if action=refine, only include direct_reply if action=direct_reply""",

            "image_analysis": """You are analyzing a user message that includes an image attachment.

The user message is: "{user_message}"
Has image: Yes

Decide the best action:

1. **REFINE**: If unclear what they want to know about the image
   - Examples: "what is this", "analyze", "help"
   - Provide specific analysis prompt

2. **DIRECT_REPLY**: If inappropriate image request
   - Examples: harmful content, privacy violations
   - Provide polite refusal

3. **PASS_THROUGH**: If clear image analysis request
   - Examples: "identify this building style", "what breed is this dog"

Respond in JSON format: {{"action": "...", "refined_prompt/direct_reply": "...", "confidence": 0.XX, "reasoning": "..."}}""",

            "creative_requests": """You are analyzing a creative request (contains words like: generate, create, draw, write, make).

User message: "{user_message}"

Creative requests should be enhanced for specificity:

1. **REFINE**: If too vague or could benefit from creative enhancement
   - Examples: "write a story", "create an image", "make something cool"
   - Add specific style, genre, format, or detail requirements

2. **DIRECT_REPLY**: If inappropriate creative content
   - Examples: harmful, offensive, or illegal content requests
   - Provide polite refusal with alternatives

3. **PASS_THROUGH**: If already well-defined creative request
   - Examples: "Write a 500-word sci-fi story about time travel", "Create a minimalist logo for a coffee shop"

Respond in JSON format with enhanced creative specifications when refining."""
        }
    
    async def analyze_prompt(
        self, 
        user_message: str, 
        has_images: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> PromptAnalysisResult:
        """
        Analyze user prompt using Gemini-Flash and determine action
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Analyzing prompt: '{user_message[:50]}...' (has_images: {has_images})")
            
            # Choose appropriate analysis prompt based on content
            if has_images:
                system_prompt = self.analysis_prompts["image_analysis"].format(
                    user_message=user_message
                )
                logger.debug("Using image_analysis prompt")
            elif self._is_creative_request(user_message):
                system_prompt = self.analysis_prompts["creative_requests"].format(
                    user_message=user_message
                )
                logger.debug("Using creative_requests prompt")
            else:
                system_prompt = self.analysis_prompts["main_analysis"].format(
                    user_message=user_message
                )
                logger.debug("Using main_analysis prompt")
            
            # Call Gemini-Flash for analysis
            analysis_response = await self._call_gemini_flash(system_prompt)
            
            # Parse response
            result = self._parse_analysis_response(analysis_response)
            
            # Add timing information
            processing_time = int((time.time() - start_time) * 1000)
            result.processing_time_ms = processing_time
            
            # Update statistics
            self._update_stats(result.action, processing_time)
            
            logger.info(f"✅ Analysis complete: {result.action} (confidence: {result.confidence:.2f}, time: {processing_time}ms)")
            logger.debug(f"Reasoning: {result.reasoning}")
            
            return result
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"❌ Prompt analysis failed after {processing_time}ms: {e}")
            
            # Fallback to pass-through on error
            return PromptAnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning=f"Analysis failed, defaulting to pass-through: {str(e)}",
                confidence=0.0,
                processing_time_ms=processing_time
            )
    
    def _is_creative_request(self, message: str) -> bool:
        """Detect if this is a creative request"""
        creative_keywords = [
            "generate", "create", "draw", "write", "make", "design", 
            "compose", "craft", "build", "produce", "develop", "imagine"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in creative_keywords)
    
    async def _call_gemini_flash(self, prompt: str) -> str:
        """Call Gemini-Flash via Vertex AI for prompt analysis"""
        
        model = settings.prompt_analysis_model
        endpoint = f"https://aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{settings.vertex_ai_location}/publishers/google/models/{model}:generateContent"
        
        request_body = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": settings.prompt_analysis_temperature,
                "maxOutputTokens": 500,
                "topP": 0.8,
                "topK": 40
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"}
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.auth_handler.get_access_token()}",
            "Content-Type": "application/json"
        }
        
        logger.debug(f"Calling Gemini-Flash: {endpoint}")
        
        async with httpx.AsyncClient(timeout=settings.prompt_analysis_timeout) as client:
            response = await client.post(endpoint, headers=headers, json=request_body)
            
            if not response.is_success:
                error_text = response.text
                logger.error(f"Gemini-Flash API error: {response.status_code} - {error_text}")
                raise Exception(f"Gemini-Flash call failed: {response.status_code} - {error_text}")
            
            data = response.json()
            logger.debug(f"Gemini-Flash response: {data}")
            
            # Extract text from response
            if data.get("candidates") and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if candidate.get("content", {}).get("parts"):
                    for part in candidate["content"]["parts"]:
                        if part.get("text"):
                            return part["text"]
            
            raise Exception("No valid response from Gemini-Flash")
    
    def _parse_analysis_response(self, response: str) -> PromptAnalysisResult:
        """Parse JSON response from Gemini-Flash analysis"""
        try:
            # Clean up response - remove markdown code blocks
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
                if response.endswith("```"):
                    response = response[:-3]
            elif response.startswith("```"):
                response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]
            
            response = response.strip()
            logger.debug(f"Parsing analysis response: {response}")
            
            data = json.loads(response)
            
            # Validate action
            action_str = data.get("action", "pass_through").lower()
            if action_str not in ["refine", "direct_reply", "pass_through"]:
                logger.warning(f"Invalid action '{action_str}', defaulting to pass_through")
                action_str = "pass_through"
            
            action = AnalysisAction(action_str)
            
            # Extract fields based on action
            refined_prompt = data.get("refined_prompt") if action == AnalysisAction.REFINE else None
            direct_reply = data.get("direct_reply") if action == AnalysisAction.DIRECT_REPLY else None
            
            result = PromptAnalysisResult(
                action=action,
                refined_prompt=refined_prompt,
                direct_reply=direct_reply,
                confidence=max(0.0, min(1.0, float(data.get("confidence", 0.0)))),  # Clamp to 0-1
                reasoning=data.get("reasoning", "No reasoning provided"),
                metadata={
                    "raw_response": response,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Validate result
            if action == AnalysisAction.REFINE and not refined_prompt:
                logger.warning("REFINE action but no refined_prompt provided, switching to PASS_THROUGH")
                result.action = AnalysisAction.PASS_THROUGH
                result.reasoning = "REFINE action without refined_prompt, falling back to pass-through"
            
            if action == AnalysisAction.DIRECT_REPLY and not direct_reply:
                logger.warning("DIRECT_REPLY action but no direct_reply provided, switching to PASS_THROUGH")
                result.action = AnalysisAction.PASS_THROUGH
                result.reasoning = "DIRECT_REPLY action without direct_reply, falling back to pass-through"
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response}")
            
            # Try to extract action from text if JSON parsing fails
            response_lower = response.lower()
            if "direct_reply" in response_lower or "inappropriate" in response_lower:
                return PromptAnalysisResult(
                    action=AnalysisAction.DIRECT_REPLY,
                    direct_reply="I apologize, but I cannot process that request. Please try a different question.",
                    reasoning="Fallback parsing detected inappropriate content",
                    confidence=0.5
                )
            elif "refine" in response_lower or "unclear" in response_lower:
                return PromptAnalysisResult(
                    action=AnalysisAction.REFINE,
                    refined_prompt="Could you please provide more specific details about what you'd like help with?",
                    reasoning="Fallback parsing detected need for refinement",
                    confidence=0.5
                )
            else:
                return PromptAnalysisResult(
                    action=AnalysisAction.PASS_THROUGH,
                    reasoning=f"JSON parse error, using fallback: {str(e)}",
                    confidence=0.0
                )
        
        except Exception as e:
            logger.error(f"Unexpected error parsing analysis response: {e}")
            return PromptAnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning=f"Parse error, using fallback: {str(e)}",
                confidence=0.0
            )
    
    def _update_stats(self, action: AnalysisAction, processing_time: int):
        """Update internal statistics"""
        self.stats["total_analyses"] += 1
        
        if action == AnalysisAction.REFINE:
            self.stats["refine_count"] += 1
        elif action == AnalysisAction.DIRECT_REPLY:
            self.stats["direct_reply_count"] += 1
        else:
            self.stats["pass_through_count"] += 1
        
        # Update rolling average processing time
        current_avg = self.stats["avg_processing_time_ms"]
        total = self.stats["total_analyses"]
        self.stats["avg_processing_time_ms"] = ((current_avg * (total - 1)) + processing_time) / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        return {
            **self.stats,
            "refine_percentage": (self.stats["refine_count"] / max(1, self.stats["total_analyses"])) * 100,
            "direct_reply_percentage": (self.stats["direct_reply_count"] / max(1, self.stats["total_analyses"])) * 100,
            "pass_through_percentage": (self.stats["pass_through_count"] / max(1, self.stats["total_analyses"])) * 100
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the analyzer"""
        try:
            test_prompt = "Hello, test message for health check"
            start_time = time.time()
            
            result = await self.analyze_prompt(test_prompt)
            
            return {
                "status": "healthy",
                "response_time_ms": int((time.time() - start_time) * 1000),
                "test_result": {
                    "action": result.action.value,
                    "confidence": result.confidence
                },
                "stats": self.get_stats()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "stats": self.get_stats()
            }
```

### 2. Enhanced V2MessageTranslator Integration

```python
# Add to api/v2_translator.py

from prompt_analyzer import PromptAnalyzer, AnalysisAction
import time
from datetime import datetime

# Modify V2MessageTranslator class

class V2MessageTranslator:
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
                from auth_handler import AuthenticationHandler
                auth_handler = AuthenticationHandler(
                    credentials_path=settings.google_application_credentials
                )
                self.prompt_analyzer = PromptAnalyzer(project_id, auth_handler)
                logger.info("✅ Prompt analyzer initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize prompt analyzer: {e}")
                logger.warning("Continuing without prompt analysis")

    async def preprocess_request(self, request: V2ChatRequest) -> AsyncGenerator[V2ResponseChunk, None]:
        """Enhanced preprocessing with intelligent prompt analysis"""
        
        logger.info(f"🧠 Starting intelligent preprocessing for {len(request.contents)} content parts")
        
        # Step 1: Extract text content for analysis  
        text_parts = [part.text for part in request.contents if part.text and part.text.strip()]
        image_parts = [part for part in request.contents if part.inlineData and 
                      part.inlineData.get("mimeType", "").startswith("image/")]
        
        # Step 2: Perform intelligent analysis if enabled and text content exists
        if (self.prompt_analyzer and 
            text_parts and 
            settings.prompt_analysis_enabled and
            len(" ".join(text_parts).strip()) > 0):
            
            combined_text = " ".join(text_parts).strip()
            has_images = len(image_parts) > 0
            
            logger.info(f"🔍 Analyzing message: '{combined_text[:100]}...' (has_images: {has_images})")
            
            start_time = time.time()
            
            # Show analysis start message
            yield V2ResponseChunk(
                type="system",
                content=V2SystemMessage(
                    type="analysis_start",
                    content="🧠 Analyzing your message for optimal processing..."
                ).model_dump()
            )
            
            try:
                analysis_result = await self.prompt_analyzer.analyze_prompt(
                    combined_text, 
                    has_images=has_images,
                    context={
                        "language": request.language,
                        "session_id": request.session_id,
                        "content_parts": len(request.contents)
                    }
                )
                
                processing_time = int((time.time() - start_time) * 1000)
                logger.info(f"📊 Analysis completed in {processing_time}ms: {analysis_result.action} (confidence: {analysis_result.confidence:.2f})")
                
                # Handle analysis result
                if analysis_result.action == AnalysisAction.DIRECT_REPLY:
                    # Return direct reply to user, stop processing
                    logger.info(f"🛑 Direct reply triggered: {analysis_result.reasoning}")
                    
                    yield V2ResponseChunk(
                        type="system", 
                        content=V2SystemMessage(
                            type="analysis_complete",
                            content="Analysis complete - providing direct response"
                        ).model_dump()
                    )
                    
                    yield V2ResponseChunk(
                        type="text",
                        content=analysis_result.direct_reply,
                        is_final=True,
                        metadata={
                            "source": "prompt_analyzer",
                            "analysis_action": "direct_reply",
                            "confidence": analysis_result.confidence,
                            "processing_time_ms": processing_time,
                            "reasoning": analysis_result.reasoning,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    
                    # Signal to stop further processing
                    request._stop_processing = True
                    return
                    
                elif analysis_result.action == AnalysisAction.REFINE:
                    # Update request with refined prompt
                    logger.info(f"✨ Prompt refined: {analysis_result.reasoning}")
                    
                    yield V2ResponseChunk(
                        type="system",
                        content=V2SystemMessage(
                            type="prompt_refined", 
                            content="✨ I've enhanced your request for better results."
                        ).model_dump()
                    )
                    
                    # Replace original text with refined version
                    refined_prompt = analysis_result.refined_prompt
                    for i, part in enumerate(request.contents):
                        if part.text and part.text.strip():
                            logger.debug(f"Replacing '{part.text[:50]}...' with '{refined_prompt[:50]}...'")
                            request.contents[i].text = refined_prompt
                            break
                
                else:  # PASS_THROUGH
                    logger.info(f"➡️ Passing through original prompt: {analysis_result.reasoning}")
                    
                    yield V2ResponseChunk(
                        type="system",
                        content=V2SystemMessage(
                            type="analysis_complete",
                            content="✅ Your message is clear and ready for processing."
                        ).model_dump()
                    )
                    
            except Exception as e:
                logger.error(f"❌ Prompt analysis error: {e}")
                yield V2ResponseChunk(
                    type="system",
                    content=V2SystemMessage(
                        type="analysis_error",
                        content="⚠️ Analysis encountered an issue, proceeding with original message."
                    ).model_dump()
                )
        
        else:
            # Skip analysis if conditions not met
            if not self.prompt_analyzer:
                logger.debug("Prompt analyzer not available, skipping analysis")
            elif not text_parts:
                logger.debug("No text content found, skipping analysis")
            elif not settings.prompt_analysis_enabled:
                logger.debug("Prompt analysis disabled in settings")
        
        # Continue with existing validation logic
        validation = self.validate_user_content(request)
        if not validation["valid"]:
            logger.warning(f"Content validation issues: {validation['issues']}")
            yield V2ResponseChunk(
                type="system",
                content=V2SystemMessage(
                    type="validation_warning",
                    content=f"⚠️ Some content parts have issues: {', '.join(validation['issues'][:3])}..."
                ).model_dump()
            )
        
        # Legacy preprocessing examples (existing code)
        if text_parts:
            combined_text = " ".join(text_parts).lower()
            
            if "generate" in combined_text and "image" in combined_text:
                yield V2ResponseChunk(
                    type="system",
                    content=V2SystemMessage(
                        type="preprocessing",
                        content="🎨 I'll generate an image for you. This will consume 2 credits.",
                        action="confirm_generation"
                    ).model_dump()
                )
            
            if "analyze" in combined_text and image_parts:
                yield V2ResponseChunk(
                    type="system", 
                    content=V2SystemMessage(
                        type="preprocessing",
                        content="🔍 I'll analyze your image. This will consume 1 credit.",
                        action="confirm_analysis"
                    ).model_dump()
                )
```

### 3. Configuration Example

```python
# Add to api/config.py

class Settings(BaseSettings):
    # ... existing settings
    
    # Prompt Analysis Configuration
    prompt_analysis_enabled: bool = Field(
        default=True, 
        description="Enable intelligent prompt analysis using Gemini-Flash"
    )
    prompt_analysis_model: str = Field(
        default="gemini-2.5-flash",
        description="Model to use for prompt analysis"
    )
    prompt_analysis_temperature: float = Field(
        default=0.3,
        description="Temperature for prompt analysis (0.0-1.0, lower = more consistent)"
    )
    prompt_analysis_timeout: int = Field(
        default=30,
        description="Timeout for prompt analysis requests in seconds"
    )
    prompt_analysis_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence threshold for analysis actions"
    )
    
    # Analysis behavior settings
    enable_direct_replies: bool = Field(
        default=True,
        description="Allow prompt analyzer to reply directly to users"
    )
    enable_prompt_refinement: bool = Field(
        default=True,
        description="Allow prompt analyzer to refine user prompts"
    )
    log_analysis_decisions: bool = Field(
        default=True,
        description="Log all prompt analysis decisions for monitoring"
    )
    
    # Model aliases for analysis
    ANALYSIS_MODELS = {
        "flash": "gemini-2.5-flash",
        "flash-image": "gemini-2.5-flash-image-preview",
        "pro": "gemini-2.5-pro"
    }
    
    def get_analysis_model(self) -> str:
        """Get the full model name for prompt analysis"""
        return self.ANALYSIS_MODELS.get(self.prompt_analysis_model, self.prompt_analysis_model)
```

## Testing Examples

### Unit Test for PromptAnalyzer

```python
# tests/test_prompt_analyzer.py

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from api.prompt_analyzer import PromptAnalyzer, AnalysisAction, PromptAnalysisResult

@pytest.fixture
def mock_auth_handler():
    handler = Mock()
    handler.get_access_token.return_value = "test_token"
    return handler

@pytest.fixture
def analyzer(mock_auth_handler):
    return PromptAnalyzer("test_project", mock_auth_handler)

class TestPromptAnalyzer:
    
    @pytest.mark.asyncio
    async def test_refine_vague_request(self, analyzer):
        # Mock Gemini-Flash response
        with patch.object(analyzer, '_call_gemini_flash', return_value='{"action": "refine", "refined_prompt": "I\'d like to help you with a specific task. Could you tell me what you need assistance with?", "confidence": 0.9, "reasoning": "Request too vague"}'):
            
            result = await analyzer.analyze_prompt("help me")
            
            assert result.action == AnalysisAction.REFINE
            assert "specific task" in result.refined_prompt
            assert result.confidence == 0.9
            assert "vague" in result.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_direct_reply_inappropriate(self, analyzer):
        with patch.object(analyzer, '_call_gemini_flash', return_value='{"action": "direct_reply", "direct_reply": "I cannot help with harmful requests. Please ask something constructive.", "confidence": 0.95, "reasoning": "Inappropriate content detected"}'):
            
            result = await analyzer.analyze_prompt("how to hack someone's account")
            
            assert result.action == AnalysisAction.DIRECT_REPLY
            assert "cannot help" in result.direct_reply.lower()
            assert result.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_pass_through_clear_request(self, analyzer):
        with patch.object(analyzer, '_call_gemini_flash', return_value='{"action": "pass_through", "confidence": 0.8, "reasoning": "Clear and specific request"}'):
            
            result = await analyzer.analyze_prompt("Analyze this photo and identify the architectural style of the building")
            
            assert result.action == AnalysisAction.PASS_THROUGH
            assert result.confidence == 0.8
            assert result.refined_prompt is None
            assert result.direct_reply is None
    
    @pytest.mark.asyncio
    async def test_creative_request_detection(self, analyzer):
        assert analyzer._is_creative_request("create a story about dragons")
        assert analyzer._is_creative_request("generate an image of a sunset")
        assert analyzer._is_creative_request("write a poem")
        assert not analyzer._is_creative_request("what time is it")
    
    @pytest.mark.asyncio
    async def test_fallback_on_api_error(self, analyzer):
        with patch.object(analyzer, '_call_gemini_flash', side_effect=Exception("API Error")):
            
            result = await analyzer.analyze_prompt("test message")
            
            assert result.action == AnalysisAction.PASS_THROUGH
            assert result.confidence == 0.0
            assert "failed" in result.reasoning.lower()
    
    def test_statistics_tracking(self, analyzer):
        # Simulate some analysis results
        analyzer._update_stats(AnalysisAction.REFINE, 150)
        analyzer._update_stats(AnalysisAction.DIRECT_REPLY, 200)
        analyzer._update_stats(AnalysisAction.PASS_THROUGH, 100)
        
        stats = analyzer.get_stats()
        
        assert stats["total_analyses"] == 3
        assert stats["refine_count"] == 1
        assert stats["direct_reply_count"] == 1
        assert stats["pass_through_count"] == 1
        assert stats["refine_percentage"] == pytest.approx(33.33, rel=1e-2)
```

### Integration Test Example

```python
# tests/test_v2_integration.py

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from api.main import app

client = TestClient(app)

class TestV2Integration:
    
    @patch('api.v2_translator.PromptAnalyzer')
    def test_direct_reply_flow(self, mock_analyzer_class):
        # Setup mock analyzer to return direct reply
        mock_analyzer = Mock()
        mock_analyzer.analyze_prompt.return_value = Mock(
            action="direct_reply",
            direct_reply="I cannot help with that request. Please try something else.",
            confidence=0.9,
            reasoning="Inappropriate request"
        )
        mock_analyzer_class.return_value = mock_analyzer
        
        # Test request that should get direct reply
        response = client.post(
            "/v2/chat",
            headers={"Authorization": "Bearer test_token"},
            json={
                "contents": [{"text": "inappropriate request"}],
                "language": "en",
                "stream": True
            }
        )
        
        assert response.status_code == 200
        
        # Parse streaming response
        chunks = []
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    chunks.append(data)
                except json.JSONDecodeError:
                    continue
        
        # Should contain system message and direct reply
        system_chunks = [c for c in chunks if c.get('type') == 'system']
        text_chunks = [c for c in chunks if c.get('type') == 'text']
        
        assert len(system_chunks) >= 1  # Analysis start/complete messages
        assert len(text_chunks) == 1    # Direct reply
        assert "cannot help" in text_chunks[0]['content'].lower()
    
    @patch('api.v2_translator.PromptAnalyzer')
    def test_prompt_refinement_flow(self, mock_analyzer_class):
        # Setup mock analyzer to return refinement
        mock_analyzer = Mock()
        mock_analyzer.analyze_prompt.return_value = Mock(
            action="refine",
            refined_prompt="I'd like to help you with a specific creative writing task. What genre, length, and theme would you prefer for your story?",
            confidence=0.85,
            reasoning="Request needs specificity"
        )
        mock_analyzer_class.return_value = mock_analyzer
        
        response = client.post(
            "/v2/chat",
            headers={"Authorization": "Bearer test_token"},
            json={
                "contents": [{"text": "write me a story"}],
                "language": "en",
                "stream": True
            }
        )
        
        assert response.status_code == 200
        # Response should continue to Vertex AI with refined prompt
        # (would need to mock Vertex AI response for full test)
```

This comprehensive implementation provides a robust, production-ready prompt analysis system that integrates seamlessly with the existing V2 API architecture.