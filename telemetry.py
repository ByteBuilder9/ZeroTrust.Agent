import time
import asyncio
import logging
import aiosqlite

logger = logging.getLogger("ZeroTrust.Agent.Telemetry")

DB_PATH = "data/telemetry.db"

async def init_db():
    import os
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS interceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                session_id TEXT,
                direction TEXT,
                action TEXT,
                reason TEXT,
                latency_ms REAL
            )
        ''')
        await db.commit()
    logger.info("Telemetry database initialized.")

async def _log_to_db(session_id: str, direction: str, action: str, reason: str, latency_ms: float):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                '''INSERT INTO interceptions (timestamp, session_id, direction, action, reason, latency_ms)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (time.time(), session_id, direction, action, reason, latency_ms)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Telemetry write failed: {e}")

def fire_event(session_id: str, direction: str, action: str, reason: str, latency_ms: float):
    """
    Asynchronously fires a telemetry event without blocking the main event loop.
    """
    asyncio.create_task(_log_to_db(session_id, direction, action, reason, latency_ms))
