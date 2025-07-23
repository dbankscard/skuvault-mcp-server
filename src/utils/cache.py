"""
Simple in-memory cache for SkuVault API responses.
"""

import time
import hashlib
import json
import logging
from typing import Dict, Any, Optional, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Simple time-based cache for API responses.
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl
        
        # Different TTLs for different types of data
        self.ttl_config = {
            "warehouses": 3600,  # 1 hour - warehouses rarely change
            "product": 300,      # 5 minutes - product details
            "products": 60,      # 1 minute - product lists
            "inventory": 30,     # 30 seconds - inventory changes frequently
            "default": default_ttl
        }
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate a cache key from endpoint and parameters."""
        # Remove auth tokens from cache key
        cache_params = {k: v for k, v in params.items() 
                       if k not in ["TenantToken", "UserToken"]}
        
        # Create stable string representation
        param_str = json.dumps(cache_params, sort_keys=True)
        key_str = f"{endpoint}:{param_str}"
        
        # Return hash for shorter keys
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_ttl(self, endpoint: str) -> int:
        """Get TTL for a specific endpoint."""
        endpoint_lower = endpoint.lower()
        
        for key, ttl in self.ttl_config.items():
            if key in endpoint_lower:
                return ttl
        
        return self.default_ttl
    
    def get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached value if available and not expired.
        
        Returns:
            Cached value or None if not found/expired
        """
        cache_key = self._get_cache_key(endpoint, params)
        
        if cache_key in self.cache:
            value, expiry_time = self.cache[cache_key]
            
            if time.time() < expiry_time:
                logger.debug(f"Cache hit for {endpoint}")
                return value
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logger.debug(f"Cache expired for {endpoint}")
        
        return None
    
    def set(self, endpoint: str, params: Dict[str, Any], value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            value: Response value to cache
            ttl: Optional custom TTL in seconds
        """
        # Don't cache error responses
        if isinstance(value, dict) and "error" in value:
            return
        
        cache_key = self._get_cache_key(endpoint, params)
        ttl = ttl or self._get_ttl(endpoint)
        expiry_time = time.time() + ttl
        
        self.cache[cache_key] = (value, expiry_time)
        logger.debug(f"Cached {endpoint} for {ttl}s")
    
    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            pattern: Optional pattern to match endpoints
            
        Returns:
            Number of entries invalidated
        """
        if pattern:
            # Remove entries matching pattern
            to_remove = []
            for key in self.cache:
                if pattern.lower() in key.lower():
                    to_remove.append(key)
            
            for key in to_remove:
                del self.cache[key]
            
            logger.info(f"Invalidated {len(to_remove)} cache entries matching '{pattern}'")
            return len(to_remove)
        else:
            # Clear all
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared all {count} cache entries")
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(1 for _, (_, expiry) in self.cache.items() if expiry > current_time)
        
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "memory_usage_bytes": sum(len(str(v)) for v, _ in self.cache.values())
        }


def with_cache(cache: SimpleCache):
    """
    Decorator to add caching to async functions.
    
    Args:
        cache: SimpleCache instance to use
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, endpoint_name: str, **kwargs):
            # Check cache first
            cached_value = cache.get(endpoint_name, kwargs)
            if cached_value is not None:
                return cached_value
            
            # Call original function
            result = await func(self, endpoint_name, **kwargs)
            
            # Cache successful results
            if not (isinstance(result, dict) and "error" in result):
                cache.set(endpoint_name, kwargs, result)
            
            return result
        
        return wrapper
    return decorator


# Global cache instance
global_cache = SimpleCache()