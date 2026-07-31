"""WebSocket endpoint for real-time drift detection log streaming."""

import asyncio
import json
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.drift import subscribe, unsubscribe, get_drift_job_status

router = APIRouter()

# UUID v4 validation pattern
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@router.websocket("/ws/drift/{job_id}")
async def drift_progress_ws(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for streaming drift detection logs in real-time.

    Message types sent to client:
    - {type: "log", data: {line, stream, phase, timestamp}}
    - {type: "phase", data: {phase, message, timestamp}}
    - {type: "complete", data: {status, message, timestamp}}
    - {type: "heartbeat"}
    - {type: "error", data: {message}}
    """
    # Validate job_id format before accepting connection
    if not _UUID_PATTERN.match(job_id):
        await websocket.close(code=1008, reason="Invalid job ID format")
        return

    # Check if job exists
    job = get_drift_job_status(job_id)
    if not job:
        await websocket.accept()
        await websocket.send_text(
            json.dumps({"type": "error", "data": {"message": f"Job '{job_id}' not found"}})
        )
        await websocket.close(code=1008, reason="Job not found")
        return

    # If job already completed, send final status and close
    if job["status"] in ("completed", "failed"):
        await websocket.accept()
        await websocket.send_text(
            json.dumps({
                "type": "complete",
                "data": {
                    "status": job["status"],
                    "message": job.get("error") or job.get("result", {}).get("message", "Done"),
                },
            })
        )
        await websocket.close(code=1000, reason="Job already finished")
        return

    # Subscribe to live logs
    try:
        queue = subscribe(job_id)
    except RuntimeError as e:
        await websocket.accept()
        await websocket.send_text(
            json.dumps({"type": "error", "data": {"message": str(e)}})
        )
        await websocket.close(code=1013, reason="Too many connections")
        return

    await websocket.accept()

    try:
        while True:
            try:
                # Wait for log events with heartbeat timeout
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(json.dumps(message))

                # If this is a completion message, close gracefully
                if message.get("type") == "complete":
                    break

            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_text(json.dumps({"type": "heartbeat"}))

                # Also check if the job finished without us getting the complete event
                current_job = get_drift_job_status(job_id)
                if current_job and current_job["status"] in ("completed", "failed"):
                    await websocket.send_text(
                        json.dumps({
                            "type": "complete",
                            "data": {
                                "status": current_job["status"],
                                "message": current_job.get("error")
                                or current_job.get("result", {}).get("message", "Done"),
                            },
                        })
                    )
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        # Log but don't crash — client disconnected or network error
        pass
    finally:
        unsubscribe(job_id, queue)
