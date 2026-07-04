import os
import logging
from redis import asyncio as aioredis

logger = logging.getLogger("ZeroTrust.Agent.Ledger")

redis_client = None

async def init_redis():
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        redis_client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis State Ledger.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        # If Redis isn't strictly local during testing outside docker, allow fail gracefully for health checks.
        pass

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis State Ledger connection closed.")

async def is_session_tainted(session_id: str) -> bool:
    """
    Checks if an agent's session is flagged as high-risk/tainted.
    """
    if not redis_client:
        # Fail-closed if ledger is disconnected, unless it's just the MVP not having Redis running yet.
        # But for ZeroTrust, we should default to True (tainted) if we can't verify.
        logger.warning(f"Redis not connected. Failing closed for session {session_id}.")
        return True
        
    try:
        # A simple flag stored as a Redis key: tainted_session:{session_id}
        key = f"tainted_session:{session_id}"
        is_tainted = await redis_client.get(key)
        return is_tainted == "1"
    except Exception as e:
        logger.error(f"Redis read error: {str(e)}")
        # Fail-closed
        return True

async def mark_session_tainted(session_id: str):
    """
    Flags an agent's session as tainted, usually after it ingests untrusted data.
    """
    if not redis_client:
        return
        
    try:
        key = f"tainted_session:{session_id}"
        await redis_client.set(key, "1", ex=3600) # Taint expires after 1 hour
        logger.warning(f"Session {session_id} marked as TAINTED.")
    except Exception as e:
        logger.error(f"Redis write error: {str(e)}")
