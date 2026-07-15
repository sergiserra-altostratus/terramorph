"""WebSocket endpoint for real-time discovery progress."""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.discovery.orchestrator import subscribe, unsubscribe

router = APIRouter()


@router.websocket("/ws/discovery/{job_id}")
async def discovery_progress_ws(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for streaming discovery progress updates."""
    await websocket.accept()

    queue = subscribe(job_id)

    try:
        while True:
            try:
                # Wait for progress updates with timeout
                progress = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(json.dumps({"type": "progress", "data": progress}))

                # If the message indicates completion, close
                if progress.get("completed") == progress.get("total") and progress.get("total", 0) > 0:
                    await websocket.send_text(
                        json.dumps({"type": "complete", "data": progress})
                    )
                    break

            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_text(json.dumps({"type": "heartbeat"}))

    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe(job_id, queue)
