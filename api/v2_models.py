"""
V2 API Models and Data Structures
Extensible message type system for WonderCam v2 API
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum

class MessageType(str, Enum):
    """Supported message types in v2 API"""
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    # Future extensions: video, document, etc.

class MessageContent(BaseModel):
    """Base message content structure"""
    type: MessageType
    data: Any

class TextContent(MessageContent):
    """Text message content"""
    type: MessageType = MessageType.TEXT
    data: str = Field(description="Text content")

class ImageContent(MessageContent):
    """Image message content"""
    type: MessageType = MessageType.IMAGE
    data: str = Field(description="Base64 encoded image data")
    mime_type: Optional[str] = Field(default="image/jpeg", description="Image MIME type")

class VoiceContent(MessageContent):
    """Voice message content (future implementation)"""
    type: MessageType = MessageType.VOICE
    data: str = Field(description="Base64 encoded audio data")
    mime_type: Optional[str] = Field(default="audio/webm", description="Audio MIME type")
    duration: Optional[float] = Field(description="Duration in seconds")

class V2MessageContentSimple(BaseModel):
    """Simplified message content structure for frontend compatibility"""
    type: str = Field(description="Content type: text, image, voice")
    data: str = Field(description="Content data")
    mime_type: Optional[str] = Field(default=None, description="MIME type for binary content")

class V2Message(BaseModel):
    """V2 API Message structure"""
    role: str = Field(description="Message role: user, assistant, system")
    content: List[V2MessageContentSimple] = Field(
        description="List of message contents with different types"
    )
    timestamp: Optional[str] = Field(description="ISO timestamp")
    message_id: Optional[str] = Field(description="Unique message identifier")

# Gemini-compatible content structures
class TextPart(BaseModel):
    """Text content part"""
    text: str = Field(description="Text content")

class InlineDataPart(BaseModel):
    """Inline data (image/audio) content part"""
    inlineData: Dict[str, str] = Field(description="Inline data with mimeType and data")

class V2ContentPart(BaseModel):
    """Flexible content part - can be text or inlineData"""
    text: Optional[str] = Field(default=None, description="Text content")
    inlineData: Optional[Dict[str, str]] = Field(default=None, description="Inline data with mimeType and data")

class V2ChatRequest(BaseModel):
    """V2 API Chat Request - Simplified Gemini-compatible format"""
    contents: List[V2ContentPart] = Field(description="List of content parts (text, images, audio)")
    language: Optional[str] = Field(default="en", description="Response language preference")
    session_id: Optional[str] = Field(default=None, description="Session identifier for context")
    stream: bool = Field(default=True, description="Enable streaming response")
    
    # Processing options
    preprocessing: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Preprocessing instructions for custom logic"
    )

# Legacy format for backward compatibility
class V2ChatRequestLegacy(BaseModel):
    """V2 API Chat Request - Legacy message format"""
    messages: List[V2Message] = Field(description="Conversation history")
    language: Optional[str] = Field(default="en", description="Response language preference")
    session_id: Optional[str] = Field(description="Session identifier for context")
    stream: bool = Field(default=True, description="Enable streaming response")
    
    # Processing options
    preprocessing: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Preprocessing instructions for custom logic"
    )

class V2ResponseChunk(BaseModel):
    """V2 API Streaming Response Chunk"""
    type: str = Field(description="Chunk type: text, image, voice, system, error")
    content: Any = Field(description="Chunk content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    is_final: bool = Field(default=False, description="Indicates if this is the final chunk")

class V2ErrorResponse(BaseModel):
    """V2 API Error Response"""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    code: int = Field(description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(description="Additional error details")

class V2SystemMessage(BaseModel):
    """System messages for preprocessing interactions"""
    type: str = Field(description="System message type")
    content: str = Field(description="System message content")
    action: Optional[str] = Field(default=None, description="Action required from client")
    options: Optional[List[str]] = Field(default=None, description="Available options for user")

# Vertex AI translation structures
class VertexContent(BaseModel):
    """Vertex AI compatible content structure"""
    role: str
    parts: List[Dict[str, Any]]

class VertexRequest(BaseModel):
    """Vertex AI compatible request structure"""
    contents: List[VertexContent]
    safetySettings: List[Dict[str, Any]]
    tools: List[Any]
    generationConfig: Dict[str, Any]