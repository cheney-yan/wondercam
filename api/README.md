# Vertex AI to Gemini API Proxy

A FastAPI service that exposes a **Gemini-compatible interface** while using **Vertex AI** internally. This gives you the simplicity of Gemini's API format while leveraging Vertex AI's advanced capabilities and regional performance.

## 🚀 Features

- **Gemini-Compatible Interface**: Use familiar Gemini API format
- **Vertex AI Backend**: Leverages Vertex AI's powerful models internally
- **Smart Location Routing**: 
  - Image models use `global` endpoints for best performance
  - Text models use `australia-southeast1` (Sydney) for low latency
- **Proactive Token Management**: Automatic token refresh before expiration
- **Authentication Handling**: Manages complex Vertex AI service account authentication
- **API Key Validation**: Simple proxy authentication for client requests
- **Comprehensive Logging**: Detailed request/response logging for monitoring
- **Health Checks**: Built-in health check endpoints
- **Docker Support**: Ready-to-deploy Docker containers

## ⚡ Quick Start

### Option 1: Using Makefile (Recommended)

```bash
# Setup environment
make setup

# Edit .env with your configuration
cp .env.example .env
# Add your Google Cloud credentials path and API key

# Run the service
make run

# Or run in development mode
make dev
```

### Option 2: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json

# Proxy API Key (for client authentication)
PROXY_API_KEY=your-secret-proxy-key

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

```bash
# 3. Run the server
python run.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# Development mode with hot reload
DEBUG=True uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Docker

```bash
# Using Docker Compose
docker-compose up -d

# Or build and run manually
make build
docker run -p 8000:8000 \
  -v ./credentials.json:/app/credentials.json:ro \
  -e PROXY_API_KEY=your-secret-key \
  nightlybible/vertex-to-gemini
```

## Usage

Once the server is running, you can make requests using the **Gemini API format** - simple and clean! The service handles the complex Vertex AI authentication internally.

### Original Gemini API Request (complex auth)
```bash
curl -X POST \
  -H "x-goog-api-key: YOUR_GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent \
  -d '{
    "contents": {
      "role": "user", 
      "parts": {
        "text": "Hello, world!"
      }
    }
  }'
```

### Using Your Service (same format, Vertex AI backend)
```bash
curl -X POST \
  -H "x-goog-api-key: YOUR_PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  http://localhost:8000/v1beta/models/gemini-2.5-flash:generateContent \
  -d '{
    "contents": {
      "role": "user",
      "parts": {
        "text": "Hello, world!"
      }
    }
  }'
```

### Image Generation Example
```bash
curl -X POST \
  -H "x-goog-api-key: YOUR_PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  http://localhost:8000/v1beta/models/gemini-2.5-flash-image-preview:generateContent \
  -d '{
    "contents": {
      "role": "user",
      "parts": {
        "text": "A beautiful sunset over mountains"
      }
    }
  }'
```

**Benefits:**
- ✅ Same simple Gemini API format
- ✅ Uses powerful Vertex AI backend 
- ✅ No complex service account token handling
- ✅ Automatic authentication management
- ✅ Smart location routing (Sydney for text, Global for images)
- ✅ Proactive token refresh (1-minute buffer)

## API Endpoints

### Service Endpoints

- `GET /` - Service information and available endpoints
- `GET /health` - Health check endpoint

### Gemini-Compatible Endpoints

- `ANY /v1beta/models/{model}:{action}` - Main endpoint that accepts Gemini API format and uses Vertex AI internally

## Architecture

### Components

1. **AuthenticationHandler** (`auth_handler.py`): Manages Google Cloud service account authentication with proactive token refresh
2. **EndpointTranslator** (`endpoint_translator.py`): Translates Gemini API endpoints to Vertex AI endpoints with smart location routing
3. **Main Application** (`main.py`): FastAPI application with Gemini-compatible interface
4. **Configuration** (`config.py`): Centralized configuration management

### Request Flow

1. Client makes request using **Gemini API format** (simple!)
2. Service validates proxy API key for client authentication
3. Service determines optimal location (Sydney for text models, Global for image models)
4. Service translates Gemini endpoint to **Vertex AI endpoint** with location routing
5. Service gets access token from service account credentials (with proactive refresh)
6. Service forwards request to **Vertex AI** with proper authentication
7. Service returns response to client in **Gemini format**

## Configuration

### Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account key file (project ID auto-extracted)
- `PROXY_API_KEY`: Your API key for client authentication validation
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `DEBUG`: Enable debug mode (default: False)

### Model Location Mapping

The service automatically routes requests to optimal Vertex AI locations:

- **Text Models**: `australia-southeast1` (Sydney) - Low latency for most users
- **Image Models**: `global` - Best performance for image generation
  - `gemini-2.5-flash-image-preview`
  - Other image generation models

This routing is handled automatically - clients use the same Gemini API format regardless of the underlying Vertex AI location.

### Authentication Options

1. **Service Account Key File**: Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of your key file
2. **Application Default Credentials (ADC)**: Configure ADC using `gcloud auth application-default login`

## Error Handling

The service includes comprehensive error handling for:

- Invalid endpoint formats
- Authentication failures  
- Network connectivity issues
- API errors from Gemini
- Request/response translation errors

All errors are logged and returned with appropriate HTTP status codes.

## Development

### Running in Development Mode

```bash
# Enable debug mode and hot reload
DEBUG=True uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing

Test the service health:

```bash
curl http://localhost:8000/health
```

Test text generation:

```bash
curl -X POST \
  -H "x-goog-api-key: YOUR_PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  http://localhost:8000/v1beta/models/gemini-2.5-flash:generateContent \
  -d '{"contents": {"role": "user", "parts": {"text": "Hello"}}}'
```

Test image generation:

```bash
curl -X POST \
  -H "x-goog-api-key: YOUR_PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  http://localhost:8000/v1beta/models/gemini-2.5-flash-image-preview:generateContent \
  -d '{"contents": {"role": "user", "parts": {"text": "A beautiful landscape"}}}'
```

## License

MIT License