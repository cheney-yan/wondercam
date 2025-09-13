import os
import json
from typing import Optional
from datetime import datetime, timedelta
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
        self._token_cache = None
        
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
            
    def _is_token_expired_or_expiring_soon(self) -> bool:
        """Check if token is expired or will expire within 1 minute"""
        if not self._credentials.expiry:
            # If no expiry info, assume it needs refresh
            return True
            
        # Add 1 minute buffer for proactive refresh
        buffer = timedelta(minutes=1)
        now = datetime.utcnow()
        
        return now >= (self._credentials.expiry - buffer)
    
    def get_access_token(self) -> str:
        """Get a valid access token for Vertex AI API with proactive refresh"""
        if not self._credentials:
            self._load_credentials()
            
        # Proactive check: refresh if token is expired or expiring within 1 minute
        if not self._credentials.valid or self._is_token_expired_or_expiring_soon():
            if self._credentials.expiry:
                time_to_expiry = self._credentials.expiry - datetime.utcnow()
                logger.info(f"Token expires in {time_to_expiry.total_seconds():.1f} seconds - refreshing proactively")
            else:
                logger.info("Token validity unknown - refreshing proactively")
                
            request = Request()
            self._credentials.refresh(request)
            
            if self._credentials.expiry:
                logger.info(f"Token refreshed. New expiry: {self._credentials.expiry}")
            
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