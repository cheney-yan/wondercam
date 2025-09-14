from pydantic_settings import BaseSettings
from typing import Optional, Dict
import os


class Settings(BaseSettings):
    # Google Cloud Configuration
    google_application_credentials: Optional[str] = None
    vertex_ai_location: str = "global"  # Default to global region
    
    # Supabase Configuration
    supabase_url: str
    supabase_anon_secret: str
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Prompt Analysis Configuration
    prompt_analysis_enabled: bool = True  # Enable intelligent analysis
    prompt_analysis_timeout: int = 20  # seconds - full analysis timeout
    prompt_analysis_quick_timeout: float = 8.0  # seconds - allow more time since we notify user
    prompt_analysis_model: str = "gemini-2.5-flash-lite"
    
    # Message formatting settings
    add_message_separation: bool = True
    immediate_response_text: str = "🤖"
    use_simplified_format: bool = True
    
    # Status messages with better formatting
    status_messages: Dict[str, str] = {
        "refine": "I am generating an enhanced response based on your request...",
        "direct_reply": "Let me help you with that directly...",
        "pass_through": "Processing your request...",
    }
    
    # Direct reply templates with proper formatting
    direct_reply_templates: Dict[str, str] = {
        "inappropriate": "I cannot assist with requests that might be harmful or inappropriate.\n\nPlease feel free to ask me something else I can help with.",
        "unclear": "I'm having trouble understanding what you'd like me to help with.\n\nCould you please provide more specific details about your request?",
        "general": "I'm not able to process that particular request.\n\nIs there something else I can help you with instead?"
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()