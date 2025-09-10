"""
Query caching system for agent memory management.
Provides caching for frequently executed database queries.
"""

import time
from typing import Any, Dict, Optional, Tuple

from loguru import logger


class QueryCache:
    """Simple in-memory cache for database query results."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.access_order: Dict[str, float] = {}

    def _generate_key(self, query: str, params: Dict[str, Any]) -> str:
        """Generate a cache key from query and parameters."""
        import hashlib
        import json

        # Sort params for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True)
        key_str = f"{query}:{sorted_params}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, query: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached result if available and not expired."""
        key = self._generate_key(query, params)

        if key not in self.cache:
            return None

        result, timestamp = self.cache[key]
        current_time = time.time()

        # Check if expired
        if current_time - timestamp > self.ttl_seconds:
            del self.cache[key]
            if key in self.access_order:
                del self.access_order[key]
            return None

        # Update access time
        self.access_order[key] = current_time
        logger.debug(f"Cache hit for query: {query[:50]}...")
        return result

    def set(self, query: str, params: Dict[str, Any], result: Any) -> None:
        """Store result in cache."""
        key = self._generate_key(query, params)
        current_time = time.time()

        # Evict old entries if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[key] = (result, current_time)
        self.access_order[key] = current_time
        logger.debug(f"Cache set for query: {query[:50]}...")

    def _evict_oldest(self) -> None:
        """Remove the least recently used entry."""
        if not self.access_order:
            return

        oldest_key = min(self.access_order.keys(), key=lambda k: self.access_order[k])
        del self.cache[oldest_key]
        del self.access_order[oldest_key]

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        self.access_order.clear()
        logger.debug("Query cache cleared")

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }


# Global query cache instance
_query_cache = QueryCache()


def get_query_cache() -> QueryCache:
    """Get the global query cache instance."""
    return _query_cache


def clear_query_cache() -> None:
    """Clear the global query cache."""
    _query_cache.clear()
