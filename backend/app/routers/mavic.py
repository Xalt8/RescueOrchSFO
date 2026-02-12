"""Mavic drone control API endpoints."""

from __future__ import annotations

import asyncio
import io
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from PIL import Image
from app.schemas import (
    MavicVelocityCommand,
    MavicAltitudeCommand,
    MavicActionCommand,
    MavicStatus,
)

router = APIRouter(prefix="/mavic", tags=["Mavic Drone"])

# In-memory state (replace with Webots controller integration)
_state = {"flying": False, "altitude": 0.0, "connected": True, "last_command": None}

# Camera stream state
_camera_frame: Optional[bytes] = None
_camera_lock = threading.Lock()


@router.get("/status", response_model=MavicStatus)
def get_mavic_status():
    """Get current Mavic drone status."""
    return MavicStatus(
        connected=_state["connected"],
        flying=_state["flying"],
        altitude=_state["altitude"],
        position={"x": 0, "y": 0, "z": _state["altitude"]} if _state["flying"] else None,
    )


@router.post("/velocity")
def set_mavic_velocity(cmd: MavicVelocityCommand):
    """
    Set velocity commands for Mavic drone.
    Pitch: forward/backward, Roll: strafe, Yaw: rotate, Vertical: altitude change.
    """
    _state["last_command"] = {"type": "velocity", "data": cmd.model_dump()}
    # TODO: Forward to Webots Mavic controller (e.g., via socket/zeromq)
    return {"status": "ok", "command": _state["last_command"]}


@router.post("/altitude")
def set_mavic_altitude(cmd: MavicAltitudeCommand):
    """Set target altitude for Mavic drone in meters."""
    _state["altitude"] = cmd.altitude
    _state["last_command"] = {"type": "altitude", "data": cmd.model_dump()}
    return {"status": "ok", "target_altitude": cmd.altitude}


@router.post("/action")
def mavic_action(cmd: MavicActionCommand):
    """Execute action: takeoff, land, or hover."""
    if cmd.action not in ("takeoff", "land", "hover"):
        raise HTTPException(400, f"Invalid action: {cmd.action}")
    _state["flying"] = cmd.action == "takeoff" or (_state["flying"] and cmd.action != "land")
    if cmd.action == "takeoff" and _state["altitude"] < 0.5:
        _state["altitude"] = 1.0
    elif cmd.action == "land":
        _state["altitude"] = 0.0
    _state["last_command"] = {"type": "action", "data": cmd.model_dump()}
    return {"status": "ok", "action": cmd.action, "flying": _state["flying"]}


@router.post("/takeoff")
def mavic_takeoff():
    """Convenience endpoint: command Mavic to take off."""
    return mavic_action(MavicActionCommand(action="takeoff"))


@router.post("/land")
def mavic_land():
    """Convenience endpoint: command Mavic to land."""
    return mavic_action(MavicActionCommand(action="land"))


@router.post("/hover")
def mavic_hover():
    """Convenience endpoint: command Mavic to hover in place."""
    return mavic_action(MavicActionCommand(action="hover"))


@router.get("/command")
def get_mavic_command():
    """Get last command for Webots controller to poll."""
    cmd = _state.get("last_command") or {"type": "velocity", "data": {"pitch": 0, "roll": 0, "yaw": 0, "vertical": 0}}
    return {
        **cmd,
        "target_altitude": _state["altitude"],
        "flying": _state["flying"],
    }


@router.post("/camera/frame")
async def receive_camera_frame(request: Request):
    """Receive raw BGRA frame from Webots controller. Query: width, height (e.g. ?width=400&height=240)."""
    width = int(request.query_params.get("width", 400))
    height = int(request.query_params.get("height", 240))
    body = await request.body()
    body_bytes = bytes(body)
    expected_bgra = width * height * 4
    expected_rgb = width * height * 3
    try:
        if len(body_bytes) == expected_bgra:
            img = Image.frombytes("BGRA", (width, height), body_bytes)
            rgb = img.convert("RGB")
        elif len(body_bytes) == expected_rgb:
            img = Image.frombytes("RGB", (width, height), body_bytes)
            rgb = img
        else:
            logger.warning(
                "Camera frame size mismatch: expected %s (BGRA) or %s (RGB), got %s",
                expected_bgra,
                expected_rgb,
                len(body_bytes),
            )
            raise HTTPException(
                400,
                f"Expected {expected_bgra} (BGRA) or {expected_rgb} (RGB) bytes, got {len(body_bytes)}",
            )
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=85)
        jpeg = buf.getvalue()
        with _camera_lock:
            global _camera_frame  # noqa: PLW0603
            _camera_frame = jpeg
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "size": len(jpeg)}


async def _mjpeg_stream():
    """Async generator yielding MJPEG multipart stream."""
    boundary = b"--frame"
    while True:
        await asyncio.sleep(0.05)
        with _camera_lock:
            frame = _camera_frame
        if frame:
            yield boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"


@router.get("/camera/stream")
def mavic_camera_stream():
    """MJPEG stream of Mavic camera feed."""
    return StreamingResponse(
        _mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
