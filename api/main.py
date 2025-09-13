from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Header
import httpx
import logging

from config import settings
from supabase_auth import verify_token

from auth_handler import AuthenticationHandler
from endpoint_translator import EndpointTranslator

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Vertex AI to Gemini API Translator",
    description="A FastAPI service that translates Vertex AI authentication and endpoints to Gemini API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize global components
auth_handler = AuthenticationHandler(
    credentials_path=settings.google_application_credentials
)

# Initialize translator once we have project info
translator = None

@app.on_event("startup")
async def startup_event():
    """Initialize translator with project ID from credentials"""
    global translator
    try:
        project_id = auth_handler.get_project_id()
        translator = EndpointTranslator(project_id=project_id)
        logger.info(f"Initialized translator for project: {project_id}")
    except Exception as e:
        logger.error(f"Failed to initialize translator: {e}")
        raise



@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "vertex-gemini-translator"}


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Gemini-compatible API using Vertex AI",
        "version": "1.0.0", 
        "description": "Exposes Gemini-compatible interface while using Vertex AI internally",
        "endpoints": {
            "health": "/health",
            "gemini_api": "/v1beta/models/{model}:{action}"
        }
    }


@app.api_route("/v1beta/models/{model_action:path}", 
               methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gemini_compatible_endpoint(
    request: Request,
    model_action: str,
    user: dict = Depends(verify_token)
):
    """
    Gemini-compatible endpoint that uses Vertex AI internally
    Accepts requests like: /v1beta/models/gemini-2.5-flash:generateContent
    """
    try:
        if not translator:
            raise HTTPException(
                status_code=503,
                detail="Service not properly initialized. Please check credentials configuration."
            )
        
        # Get the original request details
        method = request.method
        headers = dict(request.headers)
        query_params = dict(request.query_params)
        
        # Get request body if present
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await request.body()
                if request_body:
                    import json
                    body = json.loads(request_body.decode('utf-8'))
                    logger.info(f"Request body parsed successfully: {len(str(body))} chars")
                else:
                    logger.info("Empty request body")
            except Exception as e:
                logger.error(f"Error parsing request body: {e}")
                raise HTTPException(status_code=400, detail="Invalid JSON in request body")
        
        # Construct the Gemini path from the request
        gemini_path = f"/v1beta/models/{model_action}"
        logger.info(f"Received {method} request for Gemini-compatible endpoint: {gemini_path}")
        
        # Get Vertex AI endpoint to call internally
        vertex_url = translator.get_vertex_endpoint(gemini_path)
        
        # Get access token for Vertex AI
        access_token = auth_handler.get_access_token()
        
        # Prepare headers for Vertex AI
        vertex_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        # Remove problematic headers
        headers_to_remove = ["host", "content-length", "authorization", "x-goog-api-key"]
        
        # Add any custom headers from original request (except auth headers)
        for key, value in headers.items():
            if key.lower() not in headers_to_remove and not key.lower().startswith("x-goog-"):
                vertex_headers[key] = value
        
        logger.info(f"Calling Vertex AI internally: {vertex_url}")
        
        # Make request to Vertex AI internally
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=method,
                url=vertex_url,
                headers=vertex_headers,
                json=body,
                params=query_params
            )
        
        logger.info(f"Vertex AI response status: {response.status_code}")
        
        # Handle the response - format as Gemini-compatible response
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                response_data = response.json()
                # Format response to match Gemini API format if needed
                gemini_response = translator.format_gemini_response(response_data)
                
                # Filter out problematic headers
                response_headers = {}
                for key, value in response.headers.items():
                    if key.lower() not in ["content-length", "transfer-encoding"]:
                        response_headers[key] = value
                
                return JSONResponse(
                    content=gemini_response,
                    status_code=response.status_code,
                    headers=response_headers
                )
            else:
                # Non-JSON response
                response_headers = {}
                for key, value in response.headers.items():
                    if key.lower() not in ["content-length", "transfer-encoding"]:
                        response_headers[key] = value
                        
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type")
                )
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return JSONResponse(
                content={"error": "Failed to process response", "detail": str(e)},
                status_code=500
            )
            
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from Vertex AI: {e}")
        return JSONResponse(
            content={"error": f"Vertex AI error: {e}"},
            status_code=e.response.status_code
        )
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")
    except ValueError as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid endpoint format: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )