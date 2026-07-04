from fastapi import APIRouter
from fastapi.responses import JSONResponse
import aiosqlite
from telemetry import DB_PATH

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/stats")
async def get_stats():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Total events
            async with db.execute("SELECT COUNT(*) as count FROM interceptions") as cursor:
                total_row = await cursor.fetchone()
                total = total_row["count"]

            # Blocked/Redacted count
            async with db.execute("SELECT COUNT(*) as count FROM interceptions WHERE action IN ('blocked', 'redacted')") as cursor:
                blocked_row = await cursor.fetchone()
                blocked = blocked_row["count"]

            # Avg Latency
            async with db.execute("SELECT AVG(latency_ms) as avg_latency FROM interceptions") as cursor:
                lat_row = await cursor.fetchone()
                avg_latency = lat_row["avg_latency"] or 0.0

            return JSONResponse(content={
                "total_inspections": total,
                "threats_mitigated": blocked,
                "average_latency_ms": round(avg_latency, 3)
            })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/logs")
async def get_logs(limit: int = 50):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM interceptions ORDER BY timestamp DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                logs = [dict(row) for row in rows]
            return JSONResponse(content={"logs": logs})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
