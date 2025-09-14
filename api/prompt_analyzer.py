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
    REFINE = "refine"           # Enhance vague/unclear prompts
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
        """Load analysis prompt templates"""
        return {
            "main_analysis": """You are a smart prompt refinement AI. Analyze the user's message and decide:

1. **REFINE**: If unclear, vague, or could benefit from enhancement
2. **DIRECT_REPLY**: If inappropriate, nonsensical, or should be declined
3. **PASS_THROUGH**: If clear, specific, and appropriate

User message: "{user_message}"
Has images: {has_images}

Image Context Guidelines:
- If user has images: Consider visual analysis context (describe, analyze, identify, compare images)
- If no images: Focus on text-only enhancement opportunities
- For image + vague text: Suggest specific image analysis actions

For DIRECT_REPLY responses, be polite, helpful, and offer alternatives when possible.
For REFINE responses, make prompts specific and actionable while preserving user intent.

Respond in JSON format:
{{
  "action": "refine|direct_reply|pass_through",
  "refined_prompt": "Enhanced specific prompt (only if action=refine)",
  "direct_reply": "Polite, helpful response with alternatives (only if action=direct_reply)",
  "confidence": 0.85,
  "reasoning": "Brief explanation"
}}""",
            
            "vague_enhancement": """The user's request is vague. Create a specific, actionable prompt that:
1. Preserves their original intent
2. Adds helpful context and structure
3. Guides toward a useful response

Original: "{original_prompt}"
Enhanced prompt: """
        }
    
    
    async def analyze_prompt(
        self,
        user_message: str,
        has_images: bool = False,
        timeout_seconds: int = 15
    ) -> AnalysisResult:
        """
        Analyze user prompt and determine appropriate action
        
        Args:
            user_message: The user's message to analyze
            has_images: Whether the message includes images
            timeout_seconds: Maximum analysis time
            
        Returns:
            AnalysisResult with action and optional refinements
        """
        start_time = time.time()
        
        try:
            # Skip analysis for very short or empty messages
            if not user_message or len(user_message.strip()) < 3:
                logger.info("🔍 Skipping analysis - message too short")
                return AnalysisResult(
                    action=AnalysisAction.PASS_THROUGH,
                    reasoning="Message too short for analysis"
                )
            
            # Run analysis with timeout
            analysis_task = asyncio.create_task(
                self._perform_analysis(user_message, has_images)
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
            logger.error(f"❌ Prompt analysis error: {e}")
            return AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning=f"Analysis error: {str(e)}"
            )
    
    async def _perform_analysis(self, user_message: str, has_images: bool, ) -> AnalysisResult:
        """Perform actual prompt analysis using Gemini-Flash"""
        
        # Create analysis prompt with language detection
        analysis_prompt = self.analysis_prompts["main_analysis"].format(
            user_message=user_message,
            has_images=str(has_images),
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
                "maxOutputTokens": 500,  # Limit output for speed
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
        endpoint = f"https://aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{settings.vertex_ai_location}/publishers/google/models/gemini-2.5-flash:generateContent"
        access_token = self.auth_handler.get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(endpoint, headers=headers, json=vertex_request)
            
            if not response.is_success:
                logger.error(f"❌ Gemini-Flash analysis failed: {response.status_code} - {response.text}")
                raise Exception(f"Analysis API error: {response.status_code}")
            
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