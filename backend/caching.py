"""
Caching module for UnderwritePro SaaS
Provides Redis-based caching with fallback to in-memory cache
"""
import os
import json
import logging
from typing import Optional, Any
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)

# Check if Redis is enabled
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Try to import Redis
try:
    import redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_ENABLED else None
    if redis_client:
        redis_client.ping()
        logger.info("Redis cache enabled")
except Exception as e:
    logger.warning(f"Redis not available, using in-memory cache: {e}")
    redis_client = None

# In-memory cache fallback
memory_cache = {}

class Cache:
    """Cache manager with Redis and in-memory fallback"""
    
    @staticmethod
    def _get_key(prefix: str, key: str) -> str:
        """Generate cache key"""
        return f"{prefix}:{key}"
    
    @staticmethod
    def get(prefix: str, key: str) -> Optional[Any]:
        """Get value from cache"""
        cache_key = Cache._get_key(prefix, key)
        
        try:
            if redis_client:
                value = redis_client.get(cache_key)
                if value:
                    return json.loads(value)
            else:
                return memory_cache.get(cache_key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    @staticmethod
    def set(prefix: str, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL in seconds"""
        cache_key = Cache._get_key(prefix, key)
        
        try:
            if redis_client:
                redis_client.setex(cache_key, ttl, json.dumps(value))
            else:
                memory_cache[cache_key] = value
                # Note: In-memory cache doesn't support TTL
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    @staticmethod
    def delete(prefix: str, key: str):
        """Delete value from cache"""
        cache_key = Cache._get_key(prefix, key)
        
        try:
            if redis_client:
                redis_client.delete(cache_key)
            else:
                memory_cache.pop(cache_key, None)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    @staticmethod
    def delete_pattern(prefix: str, pattern: str):
        """Delete all keys matching pattern"""
        try:
            if redis_client:
                keys = redis_client.keys(f"{prefix}:{pattern}")
                if keys:
                    redis_client.delete(*keys)
            else:
                # In-memory cache pattern deletion
                keys_to_delete = [
                    k for k in memory_cache.keys()
                    if k.startswith(f"{prefix}:")
                ]
                for key in keys_to_delete:
                    memory_cache.pop(key, None)
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
    
    @staticmethod
    def clear():
        """Clear all cache"""
        try:
            if redis_client:
                redis_client.flushdb()
            else:
                memory_cache.clear()
        except Exception as e:
            logger.error(f"Cache clear error: {e}")

def cache_response(prefix: str, ttl: int = 300):
    """
    Decorator to cache function responses
    
    Usage:
        @cache_response("deals", ttl=600)
        def get_deal(deal_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            key_parts = [str(arg) for arg in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
            key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached = Cache.get(prefix, key)
            if cached is not None:
                logger.debug(f"Cache hit: {prefix}:{key}")
                return cached
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            Cache.set(prefix, key, result, ttl)
            logger.debug(f"Cache miss: {prefix}:{key}")
            
            return result
        return wrapper
    return decorator

def invalidate_cache(prefix: str, pattern: str = "*"):
    """
    Invalidate cache for a specific prefix and pattern
    
    Usage:
        invalidate_cache("deals", f"{deal_id}*")
    """
    Cache.delete_pattern(prefix, pattern)

# Cache prefixes
CACHE_DEALS = "deals"
CACHE_BORROWERS = "borrowers"
CACHE_USERS = "users"
CACHE_ORGANIZATIONS = "orgs"
CACHE_UNDERWRITING = "underwriting"
CACHE_DOCUMENTS = "documents"

# Default TTLs (in seconds)
TTL_SHORT = 60          # 1 minute
TTL_MEDIUM = 300        # 5 minutes
TTL_LONG = 1800         # 30 minutes
TTL_VERY_LONG = 3600    # 1 hour
