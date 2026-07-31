"""WebSocket endpoint for real-time auto-import log streaming."""

import asyncio
import json
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.auto_import import subscribe, unsubscribe, get_auto_import_job

router = APIRouter()

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@router.websocket("/ws/auto-import/{job_id}")
async def auto_import_ws(websocket: WebSocket, job_id: str):
    """WebSocket for streaming auto-import logs.

    Message types: log, phase, complete, drift_decision, heartbeat, error.
    """
    if not _UUID_PATTERN.match(job_id):
        await websocket.close(code=1008, reason="Invalid job ID")
        return

    job = get_auto_import_job(job_id)
    if not job:
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "data": {"message": "Job not found"}}))
        await websocket.close(code=1008)
        return

    if job["status"] in ("completed", "failed", "cancelled"):
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "complete", "data": {"status": job["status"], "message": job.get("error") or "Done"}}))
        await websocket.close(code=1000)
        return

    try:
        queue = subscribe(job_id)
    except RuntimeError as e:
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "data": {"message": str(e)}}))
        await websocket.close(code=1013)
        return

    await websocket.accept()

    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(json.dumps(message))
                if message.get("type") == "complete":
                    break
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
                current = get_auto_import_job(job_id)
                if current and current["status"] in ("completed", "failed", "cancelled"):
                    await websocket.send_text(json.dumps({"type": "complete", "data": {"status": current["status"], "message": current.get("error") or "Done"}}))
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        unsubscribe(job_id, queue)
