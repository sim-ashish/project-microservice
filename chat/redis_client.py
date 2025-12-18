import redis.asyncio as redis
from typing import Dict
import json
import os

# Redis connection
redis_client: redis.Redis = None

async def get_redis():
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


async def publish_to_redis(channel: str, message: Dict):
    """Publish message to Redis channel"""
    client = await get_redis()
    await client.publish(channel, json.dumps(message))


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
