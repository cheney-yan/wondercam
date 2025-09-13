#!/usr/bin/env python3
"""
Startup script for the Vertex AI to Gemini API Translator
"""

import uvicorn
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )