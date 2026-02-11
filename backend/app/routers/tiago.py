"""Tiago robot control API endpoints."""

from fastapi import APIRouter, HTTPException
from app.schemas import (
    TiagoVelocityCommand,
    TiagoArmCommand,
    TiagoActionCommand,
    TiagoStatus,
)

router = APIRouter(prefix="/tiago", tags=["Tiago Robot"])

# In-memory state (replace with Webots controller integration)
_state = {"connected": True, "position": None, "last_command": None}


@router.get("/status", response_model=TiagoStatus)
def get_tiago_status():
    """Get current Tiago robot status."""
    return TiagoStatus(
        connected=_state["connected"],
        position=_state["position"],
        battery=100.0,
    )


@router.post("/velocity")
def set_tiago_velocity(cmd: TiagoVelocityCommand):
    """
    Set base velocity for Tiago robot.
    linear_x: forward/backward, linear_y: strafe, angular: rotation.
    """
    _state["last_command"] = {"type": "velocity", "data": cmd.model_dump()}
    # TODO: Forward to Webots Tiago controller
    return {"status": "ok", "command": _state["last_command"]}


@router.post("/arm")
def set_tiago_arm(cmd: TiagoArmCommand):
    """Command Tiago arm to a position or pose."""
    if cmd.arm not in ("left", "right"):
        raise HTTPException(400, f"Invalid arm: {cmd.arm}")
    _state["last_command"] = {"type": "arm", "data": cmd.model_dump()}
    return {"status": "ok", "command": _state["last_command"]}


@router.post("/action")
def tiago_action(cmd: TiagoActionCommand):
    """Execute action: stop, home_arms, open_gripper, close_gripper."""
    valid = ("stop", "home_arms", "open_gripper", "close_gripper")
    if cmd.action not in valid:
        raise HTTPException(400, f"Invalid action: {cmd.action}. Must be one of: {valid}")
    _state["last_command"] = {"type": "action", "data": cmd.model_dump()}
    return {"status": "ok", "action": cmd.action}


@router.post("/stop")
def tiago_stop():
    """Convenience endpoint: stop Tiago base movement."""
    return tiago_action(TiagoActionCommand(action="stop"))


@router.get("/command")
def get_tiago_command():
    """Get last command for Webots controller to poll."""
    return _state.get("last_command") or {"type": "velocity", "data": {"linear_x": 0, "linear_y": 0, "angular": 0}}
