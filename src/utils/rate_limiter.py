"""
Rate limiting and retry logic for SkuVault API calls.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter with exponential backoff for API calls.
    """
    
    def __init__(self):
        self.last_call_times: Dict[str, float] = {}
        self.retry_counts: Dict[str, int] = {}
        self.backoff_until: Dict[str, float] = {}
        
        # SkuVault rate limits (calls per minute)
        # Based on actual API responses and documentation
        self.rate_limits = {
            # Per endpoint limits we've observed
            "getwarehouses": 1,
            "getproduct": 5,
            "getproducts": 5,
            "createproduct": 5,
            "updateproduct": 5,
            "getinventorybylocation": 5,
            "setitemquantity": 5,
            "additem": 5,
            "removeitem": 5,
            # Category fallbacks
            "products": 5,
            "inventory": 5,
            "warehouses": 1,
            "default": 5
        }
    
    def get_rate_limit_key(self, endpoint: str) -> str:
        """Get the rate limit key for an endpoint."""
        endpoint_lower = endpoint.lower()
        
        # First check if we have a specific limit for this endpoint
        if endpoint_lower in self.rate_limits:
            return endpoint_lower
        
        # Otherwise, determine category
        if "product" in endpoint_lower:
            return "products"
        elif "warehouse" in endpoint_lower:
            return "warehouses"
        elif "inventory" in endpoint_lower or "location" in endpoint_lower:
            return "inventory"
        else:
            return "default"
    
    async def wait_if_needed(self, endpoint: str) -> None:
        """Wait if necessary to respect rate limits."""
        rate_key = self.get_rate_limit_key(endpoint)
        current_time = time.time()
        
        # Check if we're in backoff period
        if rate_key in self.backoff_until:
            wait_time = self.backoff_until[rate_key] - current_time
            if wait_time > 0:
                logger.info(f"Rate limit backoff for {endpoint} ({rate_key}): waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                # Clear backoff after waiting
                del self.backoff_until[rate_key]
        
        # Check regular rate limit
        if rate_key in self.last_call_times:
            time_since_last = current_time - self.last_call_times[rate_key]
            calls_per_minute = self.rate_limits.get(rate_key, 5)
            min_interval = 60.0 / calls_per_minute  # seconds between calls
            
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.debug(f"Rate limiting {endpoint}: waiting {wait_time:.1f}s (limit: {calls_per_minute}/min)")
                await asyncio.sleep(wait_time)
        
        # Update last call time
        self.last_call_times[rate_key] = time.time()
    
    def handle_rate_limit_error(self, endpoint: str, retry_after: Optional[float] = None) -> float:
        """
        Handle a rate limit error and return wait time.
        
        Args:
            endpoint: The endpoint that was rate limited
            retry_after: Suggested retry time from API
            
        Returns:
            Time to wait before retrying
        """
        rate_key = self.get_rate_limit_key(endpoint)
        
        # Increment retry count
        self.retry_counts[rate_key] = self.retry_counts.get(rate_key, 0) + 1
        
        # Calculate backoff time
        if retry_after:
            # Use API-provided retry time
            wait_time = retry_after
        else:
            # Exponential backoff: 2^retry_count seconds, max 300 seconds
            wait_time = min(2 ** self.retry_counts[rate_key], 300)
        
        # Set backoff until time
        self.backoff_until[rate_key] = time.time() + wait_time
        
        logger.warning(f"Rate limited on {endpoint}. Waiting {wait_time:.1f}s before retry.")
        
        return wait_time
    
    def reset_retry_count(self, endpoint: str) -> None:
        """Reset retry count after successful call."""
        rate_key = self.get_rate_limit_key(endpoint)
        if rate_key in self.retry_counts:
            del self.retry_counts[rate_key]
    
    def update_rate_limit_from_error(self, endpoint: str, error_message: str) -> None:
        """
        Update rate limit based on error message from API.
        
        Parses messages like: "Only 1 API calls per minute guaranteed"
        """
        import re
        
        # Try to extract rate limit from error message
        match = re.search(r'Only (\d+) API calls? per minute', error_message)
        if match:
            calls_per_minute = int(match.group(1))
            endpoint_lower = endpoint.lower()
            
            # Update the rate limit for this specific endpoint
            self.rate_limits[endpoint_lower] = calls_per_minute
            logger.info(f"Updated rate limit for {endpoint}: {calls_per_minute} calls/minute")


def with_rate_limit(rate_limiter: RateLimiter):
    """
    Decorator to add rate limiting to async functions.
    
    Args:
        rate_limiter: RateLimiter instance to use
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, endpoint_name: str, **kwargs):
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Wait if needed for rate limit
                    await rate_limiter.wait_if_needed(endpoint_name)
                    
                    # Call the original function
                    result = await func(self, endpoint_name, **kwargs)
                    
                    # Check for rate limit error in response
                    if isinstance(result, dict) and "error" in result:
                        error_msg = str(result.get("error", ""))
                        if "429" in error_msg or "rate limit" in error_msg.lower():
                            # Update rate limit from error message
                            rate_limiter.update_rate_limit_from_error(endpoint_name, error_msg)
                            
                            # Extract retry time if available
                            retry_after = None
                            if "Retry after" in error_msg:
                                try:
                                    retry_after = float(error_msg.split("Retry after")[1].split()[0])
                                except:
                                    pass
                            
                            wait_time = rate_limiter.handle_rate_limit_error(endpoint_name, retry_after)
                            
                            if retry_count < max_retries - 1:
                                await asyncio.sleep(wait_time)
                                retry_count += 1
                                continue
                    
                    # Success - reset retry count
                    rate_limiter.reset_retry_count(endpoint_name)
                    return result
                    
                except Exception as e:
                    # For other exceptions, just raise
                    raise
            
            # If we exhausted retries, return the last result
            return result
        
        return wrapper
    return decorator


# Global rate limiter instance
global_rate_limiter = RateLimiter()