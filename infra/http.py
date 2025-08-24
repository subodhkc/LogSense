"""Async HTTP client with timeout, status check, JSON/text handling."""
import asyncio
import logging
from typing import Dict, Any, Optional, Union
import httpx
from httpx import AsyncClient, Response, TimeoutException, RequestError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3
RETRY_DELAY = 1.0

class HTTPError(Exception):
    """Custom HTTP error with status code and response details."""
    def __init__(self, status_code: int, message: str, response: Optional[Response] = None):
        self.status_code = status_code
        self.response = response
        super().__init__(f"HTTP {status_code}: {message}")

class AsyncHTTPClient:
    """Async HTTP client wrapper with safety features."""
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT, max_retries: int = MAX_RETRIES):
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[AsyncClient] = None
    
    async def __aenter__(self):
        self._client = AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> Response:
        """Make HTTP request with retries and error handling."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(method, url, **kwargs)
                
                # Check for HTTP errors
                if response.status_code >= 400:
                    error_msg = f"Request failed: {method} {url}"
                    try:
                        error_detail = response.json().get("error", response.text[:200])
                        error_msg += f" - {error_detail}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                    
                    raise HTTPError(response.status_code, error_msg, response)
                
                return response
                
            except (TimeoutException, RequestError) as e:
                last_error = e
                logger.warning(f"HTTP request attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                continue
        
        raise HTTPError(0, f"Request failed after {self.max_retries} attempts: {last_error}")
    
    async def get(self, url: str, **kwargs) -> Response:
        """GET request with safety checks."""
        return await self._make_request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> Response:
        """POST request with safety checks."""
        return await self._make_request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> Response:
        """PUT request with safety checks."""
        return await self._make_request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> Response:
        """DELETE request with safety checks."""
        return await self._make_request("DELETE", url, **kwargs)
    
    async def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """GET request returning JSON with validation."""
        response = await self.get(url, **kwargs)
        try:
            return response.json()
        except ValueError as e:
            raise HTTPError(response.status_code, f"Invalid JSON response: {e}", response)
    
    async def post_json(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None, 
        **kwargs
    ) -> Dict[str, Any]:
        """POST request with JSON data, returning JSON."""
        if data is not None:
            kwargs["json"] = data
        
        response = await self.post(url, **kwargs)
        try:
            return response.json()
        except ValueError as e:
            raise HTTPError(response.status_code, f"Invalid JSON response: {e}", response)

# Convenience functions for one-off requests
async def get_json(url: str, timeout: float = DEFAULT_TIMEOUT, **kwargs) -> Dict[str, Any]:
    """Convenience function for single GET JSON request."""
    async with AsyncHTTPClient(timeout=timeout) as client:
        return await client.get_json(url, **kwargs)

async def post_json(
    url: str, 
    data: Optional[Dict[str, Any]] = None, 
    timeout: float = DEFAULT_TIMEOUT, 
    **kwargs
) -> Dict[str, Any]:
    """Convenience function for single POST JSON request."""
    async with AsyncHTTPClient(timeout=timeout) as client:
        return await client.post_json(url, data, **kwargs)
