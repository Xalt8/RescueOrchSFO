"""Tiago controller that polls Rescue Command Center API and applies base velocity."""

import json
import urllib.request
import urllib.error
from controller import Robot

# Use 127.0.0.1 (more reliable than localhost on some systems)
DEFAULT_API = "http://127.0.0.1:8000"
WHEEL_RADIUS = 0.0985
WHEEL_BASE = 0.4044  # distance between wheels

def fetch_command(api_url):
    try:
        req = urllib.request.Request(f"{api_url}/tiago/command")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def main():
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    print("=== Tiago++ Devices ===")
    for i in range(robot.getNumberOfDevices()):
        dev = robot.getDeviceByIndex(i)
        print(f"Device {i}: {dev.getName()}")

    wheel_left = robot.getDevice("wheel_left_joint")
    wheel_right = robot.getDevice("wheel_right_joint")
    wheel_left.setPosition(float("inf"))
    wheel_right.setPosition(float("inf"))

    # Get API URL from controller args (optional), e.g. controllerArgs "http://127.0.0.1:8000"
    try:
        args = robot.getControllerArguments()
        api_url = (args[0] if isinstance(args, (list, tuple)) and args else args or DEFAULT_API) or DEFAULT_API
    except Exception:
        api_url = DEFAULT_API

    poll_counter = 0
    cmd = None
    linear_x = linear_y = angular = 0.0
    api_connected = False

    while robot.step(timestep) != -1:
        poll_counter += 1

        # Poll API every ~32ms for responsive control
        if poll_counter >= 4:
            poll_counter = 0
            cmd = fetch_command(api_url)
            if cmd and not api_connected:
                api_connected = True
                print("[tiago_api] Connected to Rescue Command Center API")
            if cmd and cmd.get("type") == "velocity":
                data = cmd.get("data", {})
                linear_x = data.get("linear_x", 0)
                linear_y = data.get("linear_y", 0)
                angular = data.get("angular", 0)
            elif cmd and cmd.get("type") == "action" and cmd.get("data", {}).get("action") == "stop":
                linear_x = linear_y = angular = 0.0

        # Differential drive: v_left = linear - angular * L/2, v_right = linear + angular * L/2
        # Convert m/s to rad/s: omega = v / r
        left_vel = (linear_x - angular * WHEEL_BASE / 2) / WHEEL_RADIUS
        right_vel = (linear_x + angular * WHEEL_BASE / 2) / WHEEL_RADIUS

        wheel_left.setVelocity(max(-10, min(10, left_vel)))
        wheel_right.setVelocity(max(-10, min(10, right_vel)))


if __name__ == "__main__":
    main()
