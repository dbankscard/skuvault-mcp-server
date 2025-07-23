"""
SkuVault API client for making authenticated requests.
"""

import json
import logging
from typing import Dict, Any, Optional, TypeVar, Type
from pathlib import Path

import httpx
from pydantic import BaseModel

from .models.skuvault import AuthTokens, GetTokensRequest, GetTokensResponse, BaseRequest
from .utils.rate_limiter import with_rate_limit, global_rate_limiter
from .utils.cache import with_cache, global_cache

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class SkuVaultAPIError(Exception):
    """Custom exception for SkuVault API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class SkuVaultClient:
    """Client for interacting with the SkuVault API."""
    
    BASE_URL = "https://app.skuvault.com/api"
    
    def __init__(self, tenant_token: Optional[str] = None, user_token: Optional[str] = None):
        """
        Initialize the SkuVault client.
        
        Args:
            tenant_token: SkuVault tenant token
            user_token: SkuVault user token
        """
        self.auth_tokens = AuthTokens(
            TenantToken=tenant_token or "",
            UserToken=user_token or ""
        ) if tenant_token and user_token else None
        
        # Connection pooling for better performance
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30.0,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0
            )
        )
        
        # Load API schema
        schema_path = Path(__file__).parent.parent / "api_schema_complete.json"
        with open(schema_path, 'r') as f:
            self.api_schema = json.load(f)
    
    async def authenticate(self, email: str, password: str) -> AuthTokens:
        """
        Authenticate with SkuVault and obtain tokens.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Authentication tokens
        """
        request = GetTokensRequest(Email=email, Password=password)
        response = await self._make_request(
            "/gettokens",
            request,
            GetTokensResponse,
            skip_auth=True
        )
        
        self.auth_tokens = AuthTokens(
            TenantToken=response.TenantToken,
            UserToken=response.UserToken
        )
        
        return self.auth_tokens
    
    async def _make_request(
        self,
        endpoint: str,
        request_model: BaseModel,
        response_model: Type[T],
        skip_auth: bool = False
    ) -> T:
        """
        Make an authenticated request to the SkuVault API.
        
        Args:
            endpoint: API endpoint path
            request_model: Pydantic model instance for the request
            response_model: Pydantic model class for the response
            skip_auth: Skip adding authentication tokens
            
        Returns:
            Parsed response as the specified model
        """
        # Add authentication tokens if not skipping
        if not skip_auth:
            if not self.auth_tokens:
                raise SkuVaultAPIError("Authentication required. Call authenticate() first.")
            
            # Add auth tokens to request data
            request_data = request_model.model_dump()
            request_data.update(self.auth_tokens.model_dump())
        else:
            request_data = request_model.model_dump()
        
        # Make the request
        try:
            response = await self.client.post(endpoint, json=request_data)
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Check for API-level errors
            if isinstance(response_data, dict):
                if response_data.get("Status") == "Error":
                    errors = response_data.get("Errors", ["Unknown error"])
                    raise SkuVaultAPIError(
                        f"API Error: {', '.join(errors)}",
                        response_data=response_data
                    )
            
            # Parse into response model
            return response_model.model_validate(response_data)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise SkuVaultAPIError(
                f"HTTP {e.response.status_code} error",
                status_code=e.response.status_code
            )
        except Exception as e:
            logger.error(f"Unexpected error for {endpoint}: {e}")
            raise SkuVaultAPIError(f"Request failed: {str(e)}")
    
    @with_rate_limit(global_rate_limiter)
    @with_cache(global_cache)
    async def call_endpoint(self, endpoint_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call any SkuVault API endpoint by name.
        
        Args:
            endpoint_name: Name of the endpoint (e.g., "getproduct")
            **kwargs: Parameters for the endpoint
            
        Returns:
            API response as a dictionary
        """
        # Find endpoint in schema
        endpoint_info = self.api_schema["endpoints"].get(endpoint_name.lower())
        if not endpoint_info:
            raise SkuVaultAPIError(f"Unknown endpoint: {endpoint_name}")
        
        # Get category to construct proper URL
        category = endpoint_info.get("category", "general")
        
        # Construct URL path - SkuVault uses /api/{category}/{endpoint}
        endpoint_path = endpoint_info.get("url", f"/{endpoint_name}")
        if endpoint_path.startswith("/"):
            endpoint_path = endpoint_path[1:]  # Remove leading slash
            
        url = f"/{category}/{endpoint_path}"
        
        # Add authentication
        if not self.auth_tokens:
            raise SkuVaultAPIError("Authentication required. Call authenticate() first.")
        
        request_data = {
            **self.auth_tokens.model_dump(),
            **kwargs
        }
        
        # Make request
        try:
            response = await self.client.post(url, json=request_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {endpoint_name}: {e}")
            raise SkuVaultAPIError(
                f"HTTP {e.response.status_code} error",
                status_code=e.response.status_code
            )
        except Exception as e:
            logger.error(f"Unexpected error for {endpoint_name}: {e}")
            raise SkuVaultAPIError(f"Request failed: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()