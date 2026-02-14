"""Pydantic schemas for Rescue Command Center API."""

from pydantic import BaseModel, Field
from typing import Optional


# --- Mavic (Drone) Schemas ---

class MavicVelocityCommand(BaseModel):
    """Velocity command for Mavic drone - pitch, roll, yaw, vertical."""
    pitch: float = Field(0.0, ge=-2.0, le=2.0, description="Forward/backward (- back, + forward)")
    roll: float = Field(0.0, ge=-1.0, le=1.0, description="Strafe left/right (- right, + left)")
    yaw: float = Field(0.0, ge=-1.5, le=1.5, description="Rotate (- right, + left)")
    vertical: float = Field(0.0, ge=-1.0, le=1.0, description="Altitude (- down, + up)")


class MavicAltitudeCommand(BaseModel):
    """Set target altitude for Mavic drone."""
    altitude: float = Field(1.0, ge=0.0, le=50.0, description="Target altitude in meters")


class MavicActionCommand(BaseModel):
    """Action command for Mavic: takeoff, land, hover."""
    action: str = Field(..., description="One of: takeoff, land, hover")


class MavicStatus(BaseModel):
    """Current Mavic status."""
    connected: bool = False
    flying: bool = False
    altitude: float = 0.0
    position: Optional[dict] = None


# --- Tiago (Robot) Schemas ---

class TiagoVelocityCommand(BaseModel):
    """Velocity command for Tiago robot base."""
    linear_x: float = Field(0.0, ge=-3.0, le=3.0, description="Forward/backward velocity (m/s)")
    linear_y: float = Field(0.0, ge=-3.0, le=3.0, description="Strafe left/right velocity (m/s)")
    angular: float = Field(0.0, ge=-3.0, le=3.0, description="Rotational velocity (rad/s)")


class TiagoArmCommand(BaseModel):
    """Arm pose command for Tiago."""
    arm: str = Field("right", description="'left' or 'right' arm")
    joint_positions: Optional[list[float]] = Field(None, description="Joint positions for 7 arm joints")
    pose: Optional[dict] = None  # x, y, z, roll, pitch, yaw


class TiagoHeadCommand(BaseModel):
    """Head control command for Tiago."""
    head_1: float = Field(0.0, ge=-1.57, le=1.57, description="Head pan (left/right) in radians")
    head_2: float = Field(0.0, ge=-1.57, le=1.57, description="Head tilt (up/down) in radians")


class TiagoTorsoCommand(BaseModel):
    """Torso lift command for Tiago."""
    height: float = Field(0.0, ge=0.0, le=0.35, description="Torso lift height in meters (0-0.35m)")


class TiagoGripperCommand(BaseModel):
    """Gripper command for Tiago."""
    arm: str = Field("right", description="'left' or 'right' arm")
    action: str = Field(..., description="'open' or 'close' gripper")


class TiagoActionCommand(BaseModel):
    """Action command for Tiago: stop, home_arms, etc."""
    action: str = Field(..., description="One of: stop, home_arms, open_gripper, close_gripper")



class TiagoPositionUpdate(BaseModel):
    """Position update for Tiago robot."""
    x: float
    y: float
    z: float
    yaw: Optional[float] = None


class TiagoStatus(BaseModel):
    """Current Tiago status."""
    connected: bool = False
    position: Optional[dict] = None
    battery: Optional[float] = None
