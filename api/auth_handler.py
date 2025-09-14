import os
import json
from typing import Optional
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)


class AuthenticationHandler:
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
        self.project_id = None
        self._credentials = None
        
    def _load_credentials(self):
        """Load Google Cloud credentials and extract project ID"""
        try:
            if self.credentials_path and os.path.exists(self.credentials_path):
                # Use service account key file
                logger.info(f"Loading credentials from {self.credentials_path}")
                self._credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                
                # Extract project ID from credentials file
                with open(self.credentials_path, 'r') as f:
                    cred_data = json.load(f)
                    self.project_id = cred_data.get('project_id')
                    logger.info(f"Extracted project ID: {self.project_id}")
                    
            else:
                # Use application default credentials (ADC)
                logger.info("Loading application default credentials")
                self._credentials, project = default(
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.project_id = project
                logger.info(f"Using project ID from ADC: {self.project_id}")
                    
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise
            
    def get_access_token(self) -> str:
        """Get a valid access token for Vertex AI API"""
        if not self._credentials:
            self._load_credentials()
            
        # Simple check: refresh if credentials are not valid
        if not self._credentials.valid:
            logger.info("Refreshing invalid credentials")
            request = Request()
            self._credentials.refresh(request)
            logger.info("Token refreshed successfully")
            
        if not self._credentials.token:
            logger.error("Failed to obtain access token")
            raise Exception("Unable to obtain valid access token")
            
        return self._credentials.token
    
    def get_project_id(self) -> str:
        """Get the Google Cloud project ID"""
        if not self.project_id:
            if not self._credentials:
                self._load_credentials()
        return self.project_id