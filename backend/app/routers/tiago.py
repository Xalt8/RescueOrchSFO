"""Tiago robot control API endpoints."""

from fastapi import APIRouter, HTTPException
from app.schemas import (
    TiagoVelocityCommand,
    TiagoArmCommand,
    TiagoHeadCommand,
    TiagoTorsoCommand,
    TiagoGripperCommand,
    TiagoActionCommand,
    TiagoStatus,
    TiagoPositionUpdate,
)

# --- New endpoint: update Tiago position ---
from fastapi import Body

router = APIRouter(prefix="/tiago", tags=["Tiago Robot"])


@router.post("/{robot_id}/position")
@router.post("/position")
def update_tiago_position(
    pos: TiagoPositionUpdate = Body(...), robot_id: str = "1"
):
    """Update Tiago's real position (called by controller)."""
    state = _get_state(robot_id)
    state["position"] = {"x": pos.x, "y": pos.y, "z": pos.z}
    return {"status": "ok", "position": state["position"], "robot_id": robot_id}


# In-memory state for multiple Tiago robots (replace with Webots controller integration)
_states = {
    "1": {"connected": True, "position": None, "last_command": None},
    "2": {"connected": True, "position": None, "last_command": None},
    "3": {"connected": True, "position": None, "last_command": None},
}


def _get_state(robot_id: str = "1"):
    """Get state for a specific robot, defaulting to robot 1."""
    if robot_id not in _states:
        robot_id = "1"
    return _states[robot_id]


@router.get("/{robot_id}/status", response_model=TiagoStatus)
@router.get("/status", response_model=TiagoStatus)
def get_tiago_status(robot_id: str = "1"):
    """Get current Tiago robot status. robot_id: 1, 2, or 3."""
    state = _get_state(robot_id)
    return TiagoStatus(
        connected=state["connected"],
        position=state["position"],
        battery=100.0,
    )


@router.post("/{robot_id}/velocity")
@router.post("/velocity")
def set_tiago_velocity(cmd: TiagoVelocityCommand, robot_id: str = "1"):
    """
    Set base velocity for Tiago robot.
    linear_x: forward/backward, linear_y: strafe, angular: rotation.
    robot_id: 1, 2, or 3.
    """
    state = _get_state(robot_id)
    state["last_command"] = {"type": "velocity", "data": cmd.model_dump()}
    # TODO: Forward to Webots Tiago controller
    return {"status": "ok", "command": state["last_command"], "robot_id": robot_id}


@router.post("/{robot_id}/arm")
@router.post("/arm")
def set_tiago_arm(cmd: TiagoArmCommand, robot_id: str = "1"):
    """Command Tiago arm to a position or pose. robot_id: 1, 2, or 3."""
    if cmd.arm not in ("left", "right"):
        raise HTTPException(400, f"Invalid arm: {cmd.arm}")
    state = _get_state(robot_id)
    state["last_command"] = {"type": "arm", "data": cmd.model_dump()}
    return {"status": "ok", "command": state["last_command"], "robot_id": robot_id}


@router.post("/{robot_id}/head")
@router.post("/head")
def set_tiago_head(cmd: TiagoHeadCommand, robot_id: str = "1"):
    """Control Tiago head pan and tilt. robot_id: 1, 2, or 3."""
    state = _get_state(robot_id)
    state["last_command"] = {"type": "head", "data": cmd.model_dump()}
    return {"status": "ok", "command": state["last_command"], "robot_id": robot_id}


@router.post("/{robot_id}/torso")
@router.post("/torso")
def set_tiago_torso(cmd: TiagoTorsoCommand, robot_id: str = "1"):
    """Control Tiago torso lift height. robot_id: 1, 2, or 3."""
    state = _get_state(robot_id)
    state["last_command"] = {"type": "torso", "data": cmd.model_dump()}
    return {"status": "ok", "command": state["last_command"], "robot_id": robot_id}


@router.post("/{robot_id}/gripper")
@router.post("/gripper")
def set_tiago_gripper(cmd: TiagoGripperCommand, robot_id: str = "1"):
    """Control Tiago gripper (open/close). robot_id: 1, 2, or 3."""
    if cmd.arm not in ("left", "right"):
        raise HTTPException(400, f"Invalid arm: {cmd.arm}")
    if cmd.action not in ("open", "close"):
        raise HTTPException(400, f"Invalid action: {cmd.action}. Must be 'open' or 'close'")
    state = _get_state(robot_id)
    state["last_command"] = {"type": "gripper", "data": cmd.model_dump()}
    return {"status": "ok", "command": state["last_command"], "robot_id": robot_id}


@router.post("/{robot_id}/action")
@router.post("/action")
def tiago_action(cmd: TiagoActionCommand, robot_id: str = "1"):
    """Execute action: stop, home_arms, open_gripper, close_gripper. robot_id: 1, 2, or 3."""
    valid = ("stop", "home_arms", "open_gripper", "close_gripper")
    if cmd.action not in valid:
        raise HTTPException(400, f"Invalid action: {cmd.action}. Must be one of: {valid}")
    state = _get_state(robot_id)
    state["last_command"] = {"type": "action", "data": cmd.model_dump()}
    return {"status": "ok", "action": cmd.action, "robot_id": robot_id}


@router.post("/{robot_id}/stop")
@router.post("/stop")
def tiago_stop(robot_id: str = "1"):
    """Convenience endpoint: stop Tiago base movement. robot_id: 1, 2, or 3."""
    return tiago_action(TiagoActionCommand(action="stop"), robot_id=robot_id)


@router.get("/{robot_id}/command")
@router.get("/command")
def get_tiago_command(robot_id: str = "1"):
    """Get last command for Webots controller to poll. robot_id: 1, 2, or 3."""
    state = _get_state(robot_id)
    return state.get("last_command") or {"type": "velocity", "data": {"linear_x": 0, "linear_y": 0, "angular": 0}}
