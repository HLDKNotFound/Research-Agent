import hashlib
import json
import logging
from typing import Any, Optional, Union
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Production-grade Redis Cache Service with versioning, namespacing, and graceful degradation."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.version = settings.CACHE_VERSION
        self.enabled = settings.REDIS_ENABLED
        self._client: Optional[aioredis.Redis] = None

    async def get_client(self) -> Optional[aioredis.Redis]:
        if not self.enabled:
            return None
        if self._client is None:
            try:
                self._client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Redis connection: {e}. Falling back to non-cached mode.")
                return None
        return self._client

    def build_key(self, namespace: str, entity_id: str, *subkeys: Any, **filters: Any) -> str:
        """
        Builds a versioned, namespaced cache key.
        Format: {version}:{namespace}:{entity_id}:{subkeys}:{filters_hash}
        Example: v1:projects:list:usr_123:page=1:limit=20:a7b8c9d0
        """
        key_parts = [self.version, namespace, str(entity_id)]

        if subkeys:
            key_parts.extend([str(k) for k in subkeys if k is not None])

        if filters:
            # Sort filters deterministically and hash
            sorted_filters = sorted((k, v) for k, v in filters.items() if v is not None)
            if sorted_filters:
                filter_str = json.dumps(sorted_filters, sort_keys=True, default=str)
                filters_hash = hashlib.md5(filter_str.encode("utf-8")).hexdigest()[:8]
                key_parts.append(f"h_{filters_hash}")

        return ":".join(key_parts)

    async def get(self, key: str) -> Optional[Any]:
        """Fetch and deserialize a value from Redis. Returns None on cache miss or connection error."""
        try:
            client = await self.get_client()
            if client is None:
                return None
            raw_data = await client.get(key)
            if raw_data is not None:
                return json.loads(raw_data)
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Serialize and set a value with TTL. Returns True on success, False otherwise."""
        try:
            client = await self.get_client()
            if client is None:
                return False
            ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_DEFAULT_TTL_SECONDS
            serialized = json.dumps(value, default=str)
            await client.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete an exact key."""
        try:
            client = await self.get_client()
            if client is None:
                return False
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{key}': {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Deletes all keys matching the given pattern across the versioned namespace.
        Example: delete_pattern("v1:projects:list:*") or delete_pattern("v1:projects:*")
        """
        try:
            client = await self.get_client()
            if client is None:
                return 0

            cursor = 0
            deleted_count = 0
            while True:
                cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted_count += await client.delete(*keys)
                if cursor == 0:
                    break
            return deleted_count
        except Exception as e:
            logger.warning(f"Cache delete_pattern failed for pattern '{pattern}': {e}")
            return 0

    async def invalidate_project(self, project_id: Union[str, Any], user_id: Optional[Union[str, Any]] = None) -> None:
        """Invalidates all caches related to a project and user project listings."""
        p_id = str(project_id)
        await self.delete(f"{self.version}:projects:detail:{p_id}")
        await self.delete_pattern(f"{self.version}:conversations:list:{p_id}:*")
        await self.delete_pattern(f"{self.version}:files:list:{p_id}:*")
        await self.delete_pattern(f"{self.version}:reports:list:{p_id}:*")
        if user_id:
            await self.delete_pattern(f"{self.version}:projects:list:{user_id}:*")
        else:
            await self.delete_pattern(f"{self.version}:projects:list:*")

    async def invalidate_conversation(self, conversation_id: Union[str, Any], project_id: Optional[Union[str, Any]] = None) -> None:
        """Invalidates conversation detail, message list, and project conversation lists."""
        c_id = str(conversation_id)
        await self.delete(f"{self.version}:conversations:detail:{c_id}")
        await self.delete_pattern(f"{self.version}:messages:list:{c_id}:*")
        if project_id:
            await self.delete_pattern(f"{self.version}:conversations:list:{project_id}:*")

    async def invalidate_report(self, report_id: Union[str, Any], run_id: Optional[Union[str, Any]] = None, project_id: Optional[Union[str, Any]] = None) -> None:
        """Invalidates report detail and associated sections/citations."""
        r_id = str(report_id)
        await self.delete(f"{self.version}:reports:detail:{r_id}")
        if run_id:
            await self.delete(f"{self.version}:reports:by_run:{run_id}")
        if project_id:
            await self.delete_pattern(f"{self.version}:reports:list:{project_id}:*")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


# Global singleton cache instance
cache_service = CacheService()
