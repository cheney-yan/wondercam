# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Gemini-Compatible API using Vertex AI** - a FastAPI service that exposes a simple Gemini API interface while using Vertex AI internally. This provides the simplicity of Gemini's API key authentication with the power of Vertex AI's capabilities.

## Key Features

- **Gemini-Compatible Interface**: Simple API key authentication like Gemini API
- **Vertex AI Backend**: Uses Vertex AI internally with service account authentication  
- **Endpoint Translation**: Converts Gemini API endpoints to Vertex AI endpoints internally
- **Authentication Handling**: Manages complex Vertex AI authentication automatically
- **Error Handling**: Comprehensive error handling and logging

## Architecture

### FastAPI Service Structure
- **FastAPI**: Python web framework providing Gemini-compatible interface
- **Authentication Handler**: Manages Google Cloud service account authentication
- **Endpoint Translator**: Converts Gemini API endpoints to Vertex AI endpoints internally
- **Request Proxy**: Forwards requests to Vertex AI with proper authentication

### Key Components
- `main.py`: FastAPI application with Gemini-compatible endpoints
- `auth_handler.py`: Google Cloud service account authentication
- `endpoint_translator.py`: Gemini to Vertex AI endpoint translation
- `config.py`: Centralized configuration using Pydantic settings
- `run.py`: Application startup script

## Common Development Tasks

### Setup and Installation
```bash
# Run setup script
./setup.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

### Running the Server
```bash
# Production
python run.py

# Development with hot reload
DEBUG=True uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Using Docker
docker-compose up --build
```

### Testing
```bash
# Health check
curl http://localhost:8000/health

# Test Gemini-compatible endpoint (uses Vertex AI internally)
curl -X POST \
  -H "x-goog-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  http://localhost:8000/v1beta/models/gemini-2.5-flash:generateContent \
  -d '{"contents": {"role": "user", "parts": {"text": "Hello"}}}'
```

### Configuration
Environment variables in `.env`:
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key file (project ID auto-extracted)
- `PROXY_API_KEY`: Your API key for client authentication validation
- `HOST`, `PORT`: Server configuration  
- `DEBUG`: Enable debug mode

### Authentication Options
1. **Service Account Key**: Set `GOOGLE_APPLICATION_CREDENTIALS` path
2. **Application Default Credentials**: Use `gcloud auth application-default login`

## API Usage

The service accepts **Gemini API format requests** and uses **Vertex AI internally**:

### Request Format
```
POST /v1beta/models/{model}:{action}
```

Example:
```bash
# Original Gemini API request
curl -H "x-goog-api-key: YOUR_API_KEY" \
  https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent

# Using your service (same format, Vertex AI backend)
curl -H "x-goog-api-key: YOUR_API_KEY" \
  http://localhost:8000/v1beta/models/gemini-2.5-flash:generateContent
```

## File Organization

```
api/
├── main.py                 # FastAPI application
├── auth_handler.py         # Authentication management
├── endpoint_translator.py  # Endpoint translation logic
├── config.py              # Configuration settings
├── run.py                 # Startup script
├── setup.sh              # Setup script
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── Dockerfile            # Docker container
├── docker-compose.yml    # Docker Compose setup
└── README.md            # Detailed documentation
```

## Dependencies

Key Python packages:
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `httpx`: HTTP client for API requests
- `google-auth`: Google Cloud authentication
- `pydantic-settings`: Configuration management

## Error Handling

The service handles:
- Invalid endpoint formats
- Authentication failures
- Network connectivity issues
- API errors from Gemini
- Request/response translation errors

All errors are logged and returned with appropriate HTTP status codes.