import json
import logging
from app.core.redis import redis_client

logger = logging.getLogger(__name__)

TASK_LIST_TTL = 60  # seconds


def _workspace_key(workspace_id: str, suffix: str) -> str:
    return f"tasks:{workspace_id}:{suffix}"


async def get_cached(key: str) -> dict | list | None:
    """
    Cache is a performance optimization, not a source of truth — if Redis
    is unavailable, fail open and let the caller fall through to the DB.
    """
    try:
        value = await redis_client.get(key)
    except Exception:
        logger.warning("Redis unavailable, skipping cache read for key=%s", key)
        return None
    if value:
        return json.loads(value)
    return None


async def set_cached(key: str, data: dict | list, ttl: int = TASK_LIST_TTL) -> None:
    try:
        await redis_client.setex(key, ttl, json.dumps(data, default=str))
    except Exception:
        logger.warning("Redis unavailable, skipping cache write for key=%s", key)


async def invalidate_workspace_cache(workspace_id: str) -> None:
    """
    Delete all cached task list keys for a workspace.
    Called whenever a task is created, updated, or deleted.
    """
    try:
        pattern = f"tasks:{workspace_id}:*"
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
    except Exception:
        logger.warning("Redis unavailable, skipping cache invalidation for workspace=%s", workspace_id)