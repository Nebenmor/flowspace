import json
from app.core.redis import redis_client

TASK_LIST_TTL = 60  # seconds


def _workspace_key(workspace_id: str, suffix: str) -> str:
    return f"tasks:{workspace_id}:{suffix}"


async def get_cached(key: str) -> dict | list | None:
    value = await redis_client.get(key)
    if value:
        return json.loads(value)
    return None


async def set_cached(key: str, data: dict | list, ttl: int = TASK_LIST_TTL) -> None:
    await redis_client.setex(key, ttl, json.dumps(data, default=str))


async def invalidate_workspace_cache(workspace_id: str) -> None:
    """
    Delete all cached task list keys for a workspace.
    Called whenever a task is created, updated, or deleted.
    """
    pattern = f"tasks:{workspace_id}:*"
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)