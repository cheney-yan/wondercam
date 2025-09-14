"""
Vertex AI Response Formatter
Creates simplified, optimized responses in Vertex AI streaming format for frontend compatibility
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class VertexAIResponseFormatter:
    """Simplified formatter with minimal required fields for frontend compatibility"""
    
    @staticmethod
    def format_text_chunk(text: str, is_final: bool = False, add_newlines: bool = True) -> str:
        """Format text as simplified Vertex AI streaming chunk"""
        
        # Add newlines for better message separation
        formatted_text = f"{text}\n\n" if add_newlines and not is_final else text
        
        # Minimal required structure for frontend compatibility
        vertex_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": formatted_text}
                        ]
                    }
                }
            ]
        }
        
        # Only add finishReason for final responses
        if is_final:
            vertex_response["candidates"][0]["finishReason"] = "STOP"
        
        return f"data: {json.dumps(vertex_response)}\n\n"
    
    @staticmethod
    def format_immediate_response() -> str:
        """Format immediate acknowledgment - no finish reason needed, no extra newlines"""
        from config import settings
        logger.info(f"📤 Formatting immediate response: '{settings.immediate_response_text}'")
        formatted = VertexAIResponseFormatter.format_text_chunk(
            settings.immediate_response_text,
            is_final=False,
            add_newlines=False  # No extra newlines for immediate response
        )
        logger.info(f"📤 Formatted SSE data: {formatted[:100]}...")
        return formatted
    
    @staticmethod  
    def format_status_message(status_text: str) -> str:
        """Format status message - no finish reason needed"""
        from config import settings
        return VertexAIResponseFormatter.format_text_chunk(
            status_text, 
            is_final=False, 
            add_newlines=settings.add_message_separation
        )
    
    @staticmethod
    def format_direct_reply(reply_text: str) -> str:
        """Format direct reply as final response"""
        return VertexAIResponseFormatter.format_text_chunk(
            reply_text, 
            is_final=True, 
            add_newlines=False
        )
    
    @staticmethod
    def format_error_response(error_message: str) -> str:
        """Format error as final response"""
        return VertexAIResponseFormatter.format_text_chunk(
            error_message,
            is_final=True,
            add_newlines=False
        )
    
    @staticmethod
    def format_transition_message() -> str:
        """Format empty transition message before Vertex AI response"""
        return VertexAIResponseFormatter.format_text_chunk(
            "", 
            is_final=False, 
            add_newlines=False
        )

def get_enhanced_status_message(action: str) -> str:
    """Get enhanced status messages based on analysis action"""
    from config import settings
    return settings.status_messages.get(action, "Processing your request...")

def get_direct_reply_template(category: str) -> str:
    """Get direct reply template for specific categories"""
    from config import settings
    return settings.direct_reply_templates.get(category, settings.direct_reply_templates["general"])