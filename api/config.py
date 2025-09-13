from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Google Cloud Configuration
    google_application_credentials: Optional[str] = None
    
    # Supabase Configuration
    supabase_url: str
    supabase_anon_secret: str
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()