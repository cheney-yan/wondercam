"""
Intelligent Prompt Analysis Service
Uses Gemini-Flash to analyze and enhance user prompts for better AI responses
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel
import httpx

from config import settings
from auth_handler import AuthenticationHandler

logger = logging.getLogger(__name__)

class AnalysisAction(str, Enum):
    """Prompt analysis action types"""
    REFINED = "refined"           # Enhance vague/unclear prompts
    DIRECT_REPLY = "direct_reply"  # Reply directly to inappropriate/nonsensical requests
    PASS_THROUGH = "pass_through"  # Continue with original prompt

class PromptAnalysisResult(BaseModel):
    """Result of prompt analysis"""
    action: AnalysisAction
    refined_prompt: Optional[str] = None
    direct_reply: Optional[str] = None  
    confidence: float = 0.0
    reasoning: str = ""
    analysis_time_ms: int = 0

class AnalysisResult(BaseModel):
    """Simplified analysis result for internal use"""
    action: AnalysisAction
    refined_prompt: Optional[str] = None
    direct_reply: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""

class PromptAnalyzer:
    """Intelligent prompt analyzer using Gemini-Flash"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.auth_handler = AuthenticationHandler(
            credentials_path=settings.google_application_credentials
        )
        self.analysis_prompts = self._load_analysis_prompts()

        
    def _load_analysis_prompts(self) -> Dict[str, str]:
        """Load analysis prompt templates based on prompt_enhander.md"""
        return {
            "main_analysis": """Analyze and enhance prompts for image generation.

**Task**: Decide action for user input:
- "refined": Enhance vague/unclear prompts with specific details
- "direct_reply": Reply to inappropriate/nonsensical requests
- "pass_through": Continue with clear, well-structured prompts

**Rules**:
- Keep responses CONCISE (max 50 words each)
- Use detected language: {possible_language}
- For images: focus on visual analysis
- For text: focus on clarity and specificity
- Consistency: If image is provided, the refined prompt must closely be based on the image.

**JSON Response** (MUST be complete and valid):
{{
  "action": "refined|direct_reply|pass_through",
  "refined_prompt": "Short enhanced prompt (if refined)",
  "direct_reply": "Brief helpful response (if direct_reply)",
  "confidence": 0.8,
  "reasoning": "Brief reason"
}}

User: "{user_message}"
Language: {possible_language}
Has images: {has_images}""",

            "image_analysis": """You are analyzing a user request that includes images. Based on the prompt enhancer template:

**Decisions:**
1. **refined**: If the request is unclear about what to do with the image - enhance the prompt for better results
2. **direct_reply**: If the request is inappropriate or nonsensical regarding the image
3. **pass_through**: If the image request is clear and well-structured

User message: "{user_message}"
Possible Language: "{possible_language}"
Has images: {has_images}

Consider visual analysis context (describe, analyze, identify, compare images).
Respond in JSON format with action, refined_prompt/direct_reply, confidence, and reasoning.""",

            "creative_requests": """You are handling a creative image generation request. Based on the enhancement template:

**Focus on:**
- Making prompts specific and actionable for image generation
- Adding missing artistic details (style, composition, lighting, etc.)
- Clarifying technical specifications if needed
- Using the detected or possible language appropriately

User message: "{user_message}"
Possible Language: "{possible_language}"
Has images: {has_images}

Enhance vague creative requests with specific artistic requirements and technical details.
Respond in JSON format with action, refined_prompt/direct_reply, confidence, and reasoning."""
        }
    def _validate_message_quality(self, user_message: str) -> Optional[AnalysisResult]:
        """
        Validate message quality and determine if analysis should be skipped.
        
        Args:
            user_message: The user message to validate
            
        Returns:
            AnalysisResult if validation fails, None if validation passes
        """
        # Handle None/empty messages
        if user_message is None:
            return AnalysisResult(
                action=AnalysisAction.DIRECT_REPLY,
                direct_reply="😍",
                reasoning="Message is None"
            )
        
        # Normalize whitespace and check effective length
        normalized_message = user_message.strip()
        
        if not normalized_message:
            return AnalysisResult(
                action=AnalysisAction.DIRECT_REPLY,
                direct_reply="👌🏻",
                reasoning="Message is empty after normalization"
            )
        
        # Check for spam-like patterns (repeated characters)
        if self._is_spam_like(normalized_message):
            return AnalysisResult(
                action=AnalysisAction.DIRECT_REPLY,
                direct_reply="👋",
                reasoning="Spam-like pattern detected"
            )
        
        # Message passes all validations
        return None
    
    def _is_spam_like(self, message: str) -> bool:
        """
        Check if message contains spam-like patterns.
        
        Args:
            message: The normalized message to check
            
        Returns:
            True if spam-like patterns are detected
        """
        if len(message) < 10:  # Skip check for very short messages
            return False
        
        # Check for excessive character repetition (e.g., "aaaaaaa" or "hahahaha")
        char_counts = {}
        for char in message.lower():
            if char.isalpha():
                char_counts[char] = char_counts.get(char, 0) + 1
        
        total_chars = sum(char_counts.values())
        if total_chars > 0:
            max_char_ratio = max(char_counts.values()) / total_chars
            if max_char_ratio > 0.6:  # More than 60% of a single character
                return True
        
        return False

    
    async def analyze_prompt(
        self,
        user_message: str,
        has_images: bool = False,
        timeout_seconds: int = 15,
        possible_language: str = "en"
    ) -> AnalysisResult:
        """
        Analyze user prompt and determine appropriate action
        
        Args:
            user_message: The user's message to analyze
            has_images: Whether the message includes images
            timeout_seconds: Maximum analysis time
            possible_language: Detected or possible language of the message
            
        Returns:
            AnalysisResult with action and optional refinements
        """
        start_time = time.time()
        
        try:
            # Validate and filter messages based on length and content quality
            validation_result = self._validate_message_quality(user_message)
            if validation_result:
                logger.info(f"🔍 Skipping analysis - {validation_result.reasoning}")
                return validation_result
            
            # Run analysis with timeout
            analysis_task = asyncio.create_task(
                self._perform_analysis(user_message, has_images, possible_language)
            )
            
            result = await asyncio.wait_for(analysis_task, timeout=timeout_seconds)
            
            analysis_time = int((time.time() - start_time) * 1000)
            result.reasoning += f" (analyzed in {analysis_time}ms,)"
            
            logger.info(f"🧠 Analysis complete: {result.action} (confidence: {result.confidence})")
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Prompt analysis timeout after {timeout_seconds}s")
            return AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Analysis timed out for responsiveness"
            )
        except Exception as e:
            import traceback
            error_details = f"Type: {type(e).__name__}, Message: '{str(e)}', Args: {e.args}"
            logger.error(f"❌ Prompt analysis error: {error_details}")
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            return AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning=f"Analysis error: {error_details}"
            )
    
    async def _perform_analysis(self, user_message: str, has_images: bool, possible_language: str = "en") -> AnalysisResult:
        """Perform actual prompt analysis using Gemini-Flash"""
        
        # Create analysis prompt with all parameters including possible_language
        analysis_prompt = self.analysis_prompts["main_analysis"].format(
            user_message=user_message,
            has_images=str(has_images),
            possible_language=possible_language
        )
        
        # Build Vertex AI request for gemini-2.5-flash (fast analysis)
        vertex_request = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": analysis_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for consistent analysis
                "topP": 1,
                "maxOutputTokens": 2000,  # Ensure complete JSON response
                "responseMimeType": "application/json"  # Request JSON response
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"}
            ]
        }
        
        # Call Vertex AI
        endpoint = f"https://aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{settings.vertex_ai_location}/publishers/google/models/gemini-2.5-flash-lite:generateContent"
        access_token = self.auth_handler.get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(endpoint, headers=headers, json=vertex_request)
            
            if not response.is_success:
                logger.error(f"❌ Gemini-Flash analysis failed: {response.status_code} - {response.text}")
                raise Exception(f"Analysis API error: {response.status_code}")
            
            # Debug: Log the raw response for JSON parsing issues
            logger.info(f"🔍 Raw Vertex AI response: {response.text[:500]}...")
            return self._parse_analysis_response(response.text)
    
    def _parse_analysis_response(self, response: str) -> AnalysisResult:
        """Parse Gemini-Flash response into AnalysisResult"""
        try:
            # Parse Vertex AI response structure
            response_data = json.loads(response)
            
            # Extract content from candidates
            if "candidates" in response_data and len(response_data["candidates"]) > 0:
                candidate = response_data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        analysis_text = parts[0]["text"]
                        
                        # Parse the JSON content
                        analysis_json = json.loads(analysis_text)
                        
                        # Convert to AnalysisResult
                        action = AnalysisAction(analysis_json.get("action", "pass_through"))
                        
                        result = AnalysisResult(
                            action=action,
                            refined_prompt=analysis_json.get("refined_prompt"),
                            direct_reply=analysis_json.get("direct_reply"),
                            confidence=float(analysis_json.get("confidence", 0.0)),
                            reasoning=analysis_json.get("reasoning", "")
                        )
                        
                        # Enhance direct replies with better formatting
                        if result.action == AnalysisAction.DIRECT_REPLY and result.direct_reply:
                            result.direct_reply = self._enhance_direct_reply(result.direct_reply)
                        
                        return result
            
            # Fallback if parsing fails
            logger.warning("⚠️ Could not parse analysis response, defaulting to pass-through")
            return AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Response parsing failed"
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"❌ Error parsing analysis response: {e}")
            return AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning=f"Parse error: {str(e)}"
            )
    
    def _enhance_direct_reply(self, reply_text: str) -> str:
        """Enhance direct replies with better formatting"""
        reply = reply_text.strip()
        
        # Add proper paragraph separation if not already present
        if '\n' not in reply and '. ' in reply:
            # Split long sentences into paragraphs for better readability
            sentences = reply.split('. ')
            if len(sentences) > 2:
                mid_point = len(sentences) // 2
                part1 = '. '.join(sentences[:mid_point]) + '.'
                part2 = '. '.join(sentences[mid_point:])
                if not part2.endswith('.'):
                    part2 += '.'
                reply = f"{part1}\n\n{part2}"
        
        return reply

# Global analyzer instance
_analyzer: Optional[PromptAnalyzer] = None

def get_prompt_analyzer() -> Optional[PromptAnalyzer]:
    """Get global prompt analyzer instance"""
    global _analyzer
    if not _analyzer:
        try:
            auth_handler = AuthenticationHandler(
                credentials_path=settings.google_application_credentials
            )
            project_id = auth_handler.get_project_id()
            _analyzer = PromptAnalyzer(project_id)
            logger.info("✅ Prompt analyzer initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize prompt analyzer: {e}")
            return None
    return _analyzer