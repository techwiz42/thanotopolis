"""
Authentication utilities for load tests
"""
import logging
from typing import Optional, Dict, Any
import requests
from configs.settings import LoadTestConfig

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages authentication for load tests"""
    
    def __init__(self):
        self.base_url = LoadTestConfig.BASE_URL
        self.tokens: Dict[str, str] = {}
        self.organization_id: Optional[str] = None
    
    def register_test_user(self, email: str, password: str, organization_name: str) -> Optional[str]:
        """Register a new test user and return access token"""
        try:
            # Use the register/token endpoint that handles both registration and token generation
            response = requests.post(
                f"{self.base_url}/api/auth/register/token",
                json={
                    "email": email,
                    "username": email.split('@')[0],  # Use email prefix as username
                    "password": password,
                    "first_name": "Load",
                    "last_name": "Test"
                },
                headers={
                    "Content-Type": "application/json"
                },
                timeout=LoadTestConfig.DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                self.tokens[email] = access_token
                self.organization_id = data.get("organization_id")
                return access_token
            elif response.status_code == 409:
                # User already exists, try to login
                return self.login_test_user(email, password)
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return None
    
    def login_test_user(self, email: str, password: str) -> Optional[str]:
        """Login test user and return access token"""
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "email": email,
                    "password": password
                },
                headers={
                    "Content-Type": "application/json"
                },
                timeout=LoadTestConfig.DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                self.tokens[email] = access_token
                self.organization_id = data.get("organization_id")
                return access_token
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return None
    
    def get_or_create_token(self, email: str = None, password: str = None, organization_name: str = None) -> Optional[str]:
        """Get existing token or create new one"""
        if not email:
            email = LoadTestConfig.TEST_USER_EMAIL
        if not password:
            password = LoadTestConfig.TEST_USER_PASSWORD
        if not organization_name:
            organization_name = LoadTestConfig.TEST_ORGANIZATION_NAME
            
        # Check if we already have a token
        if email in self.tokens:
            return self.tokens[email]
        
        # Try to register or login
        token = self.register_test_user(email, password, organization_name)
        if not token:
            token = self.login_test_user(email, password)
            
        return token
    
    def refresh_token(self, email: str, refresh_token: str) -> Optional[str]:
        """Refresh access token"""
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/refresh",
                json={"refresh_token": refresh_token},
                timeout=LoadTestConfig.DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                self.tokens[email] = access_token
                return access_token
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return None
    
    def get_headers(self, token: str = None) -> Dict[str, str]:
        """Get headers with authentication"""
        if not token and self.tokens:
            # Use the first available token
            token = list(self.tokens.values())[0]
        return LoadTestConfig.get_headers(token)

# Global auth manager instance
auth_manager = AuthManager()