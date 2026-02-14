"""Supervisor control endpoints for direct robot movement."""

from fastapi import APIRouter

router = APIRouter(prefix="/supervisor", tags=["Supervisor"])

# Store active movements that supervisor will poll
_active_movements = {}


@router.post("/move")
def supervisor_move(data: dict):
    """
    Command supervisor to move a robot smoothly.
    
    Body:
        robot_id: str - Robot ID ("1", "2", "3")
        target: dict - Target coordinates {x, y, z}
        speed: float - Movement speed (m/s)
    """
    robot_id = data.get("robot_id")
    target = data.get("target", {})
    speed = data.get("speed", 2.5)
    
    _active_movements[robot_id] = {
        "x": target.get("x", 0),
        "y": target.get("y", 0),
        "z": target.get("z", 0.095),
        "speed": speed
    }
    
    print(f"[API] Supervisor movement command: Robot {robot_id} → ({target.get('x')}, {target.get('y')})")
    
    return {
        "status": "ok",
        "robot_id": robot_id,
        "target": target,
        "speed": speed
    }


@router.get("/movements")
def get_movements():
    """Get and clear movements (one-time fetch)."""
    global _active_movements
    movements = _active_movements.copy()
    _active_movements.clear()  # Clear after sending
    return movements


@router.delete("/movement/{robot_id}")
def clear_movement(robot_id: str):
    """Clear a specific robot's movement command."""
    if robot_id in _active_movements:
        del _active_movements[robot_id]
        return {"status": "ok", "robot_id": robot_id, "cleared": True}
    return {"status": "ok", "robot_id": robot_id, "cleared": False}