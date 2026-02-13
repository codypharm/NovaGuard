"""In-memory TTL cache for expensive API calls (OpenFDA, Nova Pro)."""

import hashlib
import logging
from functools import wraps
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Shared caches with configurable sizes and TTLs
_openfda_cache = TTLCache(maxsize=256, ttl=3600)    # 1 hour — drug labels rarely change
_research_cache = TTLCache(maxsize=128, ttl=1800)   # 30 min — research queries


def _make_key(*args, **kwargs) -> str:
    """Deterministic cache key from args."""
    raw = repr((args, sorted(kwargs.items())))
    return hashlib.md5(raw.encode()).hexdigest()


def cached_openfda(fn):
    """Cache decorator for OpenFDA label lookups."""
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        # Skip 'self' in the key (first arg)
        key = _make_key(*args[1:], **kwargs)
        if key in _openfda_cache:
            logger.debug("Cache HIT (openfda): %s", key[:8])
            return _openfda_cache[key]
        result = await fn(*args, **kwargs)
        if result is not None:  # Only cache successful lookups
            _openfda_cache[key] = result
            logger.debug("Cache SET (openfda): %s", key[:8])
        return result
    return wrapper


def cached_research(fn):
    """Cache decorator for Nova Pro research queries."""
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        key = _make_key(*args[1:], **kwargs)
        if key in _research_cache:
            logger.debug("Cache HIT (research): %s", key[:8])
            return _research_cache[key]
        result = await fn(*args, **kwargs)
        if result:  # Only cache non-empty results
            _research_cache[key] = result
            logger.debug("Cache SET (research): %s", key[:8])
        return result
    return wrapper


def clear_all_caches():
    """Manual cache invalidation (e.g., for admin/debug endpoints)."""
    _openfda_cache.clear()
    _research_cache.clear()
    logger.info("All caches cleared")
