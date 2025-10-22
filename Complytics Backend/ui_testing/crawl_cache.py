"""
Crawl Cache System
Caches discovered URLs to avoid re-crawling the same website multiple times.
Uses both in-memory cache (for fast access) and MongoDB (for persistence).
"""

import time
import hashlib
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger("crawl_cache")

# In-memory cache with TTL
_CRAWL_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour default


def _normalize_url_for_cache(url: str) -> str:
    """Normalize URL to create consistent cache key"""
    try:
        parsed = urlparse(url)
        # Use scheme + netloc as cache key (domain-level caching)
        normalized = f"{parsed.scheme}://{parsed.netloc}"
        return normalized.lower()
    except Exception:
        return url.lower()


def _generate_cache_key(url: str, max_pages: int, max_depth: int) -> str:
    """Generate cache key based on URL and crawl parameters"""
    normalized = _normalize_url_for_cache(url)
    key_string = f"{normalized}|{max_pages}|{max_depth}"
    return hashlib.md5(key_string.encode()).hexdigest()


def get_cached_crawl(
    url: str,
    max_pages: int,
    max_depth: int
) -> Optional[Dict[str, Any]]:
    """
    Get cached crawl result if available and not expired.
    
    Args:
        url: Starting URL
        max_pages: Maximum pages parameter
        max_depth: Maximum depth parameter
    
    Returns:
        Cached crawl result or None if not found/expired
    """
    cache_key = _generate_cache_key(url, max_pages, max_depth)
    
    cached = _CRAWL_CACHE.get(cache_key)
    if not cached:
        logger.info(f"❌ Crawl cache MISS for {_normalize_url_for_cache(url)}")
        return None
    
    # Check if expired
    cached_time = cached.get("cached_at", 0)
    ttl = cached.get("ttl", _CACHE_TTL_SECONDS)
    
    if time.time() - cached_time > ttl:
        # Expired, remove from cache
        logger.info(f"⏰ Crawl cache EXPIRED for {_normalize_url_for_cache(url)}")
        _CRAWL_CACHE.pop(cache_key, None)
        return None
    
    logger.info(f"✅ Crawl cache HIT for {_normalize_url_for_cache(url)}")
    logger.info(f"   Using cached {len(cached.get('result', {}).get('urls', []))} URLs from {int(time.time() - cached_time)}s ago")
    
    return cached.get("result")


def set_cached_crawl(
    url: str,
    max_pages: int,
    max_depth: int,
    crawl_result: Dict[str, Any],
    ttl: Optional[int] = None
) -> None:
    """
    Cache crawl result.
    
    Args:
        url: Starting URL
        max_pages: Maximum pages parameter
        max_depth: Maximum depth parameter
        crawl_result: Crawl result to cache
        ttl: Time-to-live in seconds (optional)
    """
    cache_key = _generate_cache_key(url, max_pages, max_depth)
    
    _CRAWL_CACHE[cache_key] = {
        "cached_at": time.time(),
        "ttl": ttl or _CACHE_TTL_SECONDS,
        "url": _normalize_url_for_cache(url),
        "max_pages": max_pages,
        "max_depth": max_depth,
        "result": crawl_result
    }
    
    logger.info(f"💾 Cached crawl result for {_normalize_url_for_cache(url)}")
    logger.info(f"   Cached {len(crawl_result.get('urls', []))} URLs with TTL={ttl or _CACHE_TTL_SECONDS}s")


def clear_cache_for_url(url: str) -> None:
    """Clear all cached entries for a specific URL"""
    normalized = _normalize_url_for_cache(url)
    removed = 0
    
    keys_to_remove = []
    for key, cached in _CRAWL_CACHE.items():
        if cached.get("url") == normalized:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        _CRAWL_CACHE.pop(key, None)
        removed += 1
    
    if removed > 0:
        logger.info(f"🗑️  Cleared {removed} cached crawl(s) for {normalized}")


def clear_all_cache() -> None:
    """Clear entire crawl cache"""
    count = len(_CRAWL_CACHE)
    _CRAWL_CACHE.clear()
    logger.info(f"🗑️  Cleared entire crawl cache ({count} entries)")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    total_entries = len(_CRAWL_CACHE)
    expired_entries = 0
    
    current_time = time.time()
    for cached in _CRAWL_CACHE.values():
        cached_time = cached.get("cached_at", 0)
        ttl = cached.get("ttl", _CACHE_TTL_SECONDS)
        if current_time - cached_time > ttl:
            expired_entries += 1
    
    return {
        "total_entries": total_entries,
        "active_entries": total_entries - expired_entries,
        "expired_entries": expired_entries,
        "cache_ttl_seconds": _CACHE_TTL_SECONDS
    }


async def persist_crawl_to_db(db, crawl_result: Dict[str, Any], url: str, organization_id: str) -> None:
    """
    Persist crawl result to MongoDB for long-term caching.
    
    Args:
        db: MongoDB database instance
        crawl_result: Crawl result to persist
        url: Starting URL
        organization_id: Organization ID
    """
    try:
        if db is None:
            return
        
        normalized_url = _normalize_url_for_cache(url)
        
        document = {
            "url": normalized_url,
            "organization_id": organization_id,
            "crawl_result": crawl_result,
            "created_at": int(time.time()),
            "expires_at": int(time.time()) + _CACHE_TTL_SECONDS
        }
        
        # Upsert: update if exists, insert if not
        await db.ui_crawl_cache.update_one(
            {"url": normalized_url, "organization_id": organization_id},
            {"$set": document},
            upsert=True
        )
        
        logger.info(f"💾 Persisted crawl to database for {normalized_url}")
    except Exception as e:
        logger.error(f"Failed to persist crawl to database: {e}")


async def get_crawl_from_db(db, url: str, organization_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve crawl result from MongoDB.
    
    Args:
        db: MongoDB database instance
        url: Starting URL
        organization_id: Organization ID
    
    Returns:
        Crawl result or None if not found/expired
    """
    try:
        if db is None:
            return None
        
        normalized_url = _normalize_url_for_cache(url)
        
        doc = await db.ui_crawl_cache.find_one({
            "url": normalized_url,
            "organization_id": organization_id,
            "expires_at": {"$gt": int(time.time())}
        })
        
        if doc:
            logger.info(f"✅ Retrieved crawl from database for {normalized_url}")
            return doc.get("crawl_result")
        
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve crawl from database: {e}")
        return None

