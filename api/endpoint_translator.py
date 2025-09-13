import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class EndpointTranslator:
    """Handles Gemini-compatible interface using Vertex AI internally"""
    
    def __init__(self, project_id: str, location: str = "global"):
        self.project_id = project_id
        self.default_location = location
        self.vertex_base_url = "https://aiplatform.googleapis.com"
        
        # Model-specific location mappings
        self.model_location_mappings = {
            "gemini-2.5-flash-image-preview": "global",
            # All other models will use australia-southeast1 (Sydney) by default
        }
        
    def get_vertex_endpoint(self, gemini_path: str) -> str:
        """
        Convert Gemini API path to Vertex AI endpoint
        
        Args:
            gemini_path: The Gemini API path from client request (e.g., /v1beta/models/gemini-2.5-flash:generateContent)
            
        Returns:
            Vertex AI URL to call internally
        """
        logger.info(f"Converting Gemini path to Vertex AI endpoint: {gemini_path}")
        
        # Extract model name and action from Gemini path
        # Handle both /v1beta/models/model:action and /v1/models/model:action patterns
        patterns = [
            r'/v1beta/models/([^:]+):(.+)',
            r'/v1/models/([^:]+):(.+)'
        ]
        
        match = None
        for pattern in patterns:
            match = re.search(pattern, gemini_path)
            if match:
                break
                
        if not match:
            raise ValueError(f"Invalid Gemini API endpoint format: {gemini_path}")
            
        model_name = match.group(1)
        action = match.group(2)
        
        logger.info(f"Extracted model: {model_name}, action: {action}")
        
        # Map to Vertex AI model name if needed
        vertex_model_name = self._map_model_name(model_name)
        
        # Determine the appropriate location for this model
        location = self._get_location_for_model(model_name)
        
        # Construct Vertex AI URL based on the example format:
        # https://aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishers/google/models/MODEL_ID:generateContent
        vertex_path = f"/v1/projects/{self.project_id}/locations/{location}/publishers/google/models/{vertex_model_name}:{action}"
        vertex_url = f"{self.vertex_base_url}{vertex_path}"
        
        logger.info(f"Will call Vertex AI at: {vertex_url}")
        
        return vertex_url
    
    def _get_location_for_model(self, model_name: str) -> str:
        """Determine the appropriate Vertex AI location for a given model"""
        # Check if there's a specific location mapping for this model
        if model_name in self.model_location_mappings:
            location = self.model_location_mappings[model_name]
            logger.info(f"Using specific location '{location}' for model '{model_name}'")
            return location
        
        # For all other models, use australia-southeast1 (Sydney) instead of global
        location = "australia-southeast1"
        logger.info(f"Using default Sydney location '{location}' for model '{model_name}'")
        return location
    
    def _map_model_name(self, gemini_model_name: str) -> str:
        """Map Gemini model names to Vertex AI model names if necessary"""
        # Most model names should be the same, but add mappings here if needed
        model_mappings = {
            # Add any specific model name mappings here if they differ
            # "gemini-model-name": "vertex-model-name"
        }
        
        return model_mappings.get(gemini_model_name, gemini_model_name)
    
    def format_gemini_response(self, vertex_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Vertex AI response to match Gemini API response format
        Most responses should be compatible, but add transformations here if necessary
        """
        # For most cases, the response format should be the same
        # Add specific transformations here if the response formats differ
        return vertex_response