"""Position tracker supervisor - monitors all robot positions and sends to API."""

import json
import urllib.request
import urllib.error
import math
from controller import Supervisor

DEFAULT_API = "http://127.0.0.1:8000"


def rotation_matrix_to_euler(rotation_matrix):
    """Convert 3x3 rotation matrix to Euler angles (roll, pitch, yaw)."""
    import math
    
    # Extract yaw (rotation around Z-axis) from rotation matrix
    # For a rotation matrix, yaw = atan2(R[1,0], R[0,0])
    yaw = math.atan2(rotation_matrix[3], rotation_matrix[0])
    
    return yaw


def send_position_to_api(api_url, robot_id, position, rotation_matrix):
    """Send robot position and orientation to backend API."""
    try:
        # Get yaw angle from rotation matrix
        yaw = rotation_matrix_to_euler(rotation_matrix)
        
        data = json.dumps({
            "x": position[0],
            "y": position[1],
            "z": position[2],
            "yaw": yaw  # Add orientation
        }).encode("utf-8")
        
        url = f"{api_url}/tiago/{robot_id}/position"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            print(f"[position_tracker] ✓ Sent robot {robot_id} pos: x={position[0]:.2f}, y={position[1]:.2f}, yaw={math.degrees(yaw):.1f}°")
            
    except urllib.error.URLError as e:
        print(f"[position_tracker] ✗ Failed to send position for robot {robot_id}: {e}")
    except OSError as e:
        print(f"[position_tracker] ✗ Network error for robot {robot_id}: {e}")


def main():
    print("[position_tracker] ===== SUPERVISOR STARTING =====")
    
    supervisor = Supervisor()
    timestep = int(supervisor.getBasicTimeStep())
    
    print(f"[position_tracker] Timestep: {timestep}ms")
    
    # Get robot references by DEF name
    print("[position_tracker] Looking for robots...")
    tiago1 = supervisor.getFromDef("TIAGO_1")
    tiago2 = supervisor.getFromDef("TIAGO_2")
    tiago3 = supervisor.getFromDef("TIAGO_3")
    
    # Verify robots were found
    if tiago1:
        print("[position_tracker] ✓ Found TIAGO_1")
    else:
        print("[position_tracker] ✗ ERROR: TIAGO_1 not found!")
        
    if tiago2:
        print("[position_tracker] ✓ Found TIAGO_2")
    else:
        print("[position_tracker] ✗ ERROR: TIAGO_2 not found!")
        
    if tiago3:
        print("[position_tracker] ✓ Found TIAGO_3")
    else:
        print("[position_tracker] ✗ ERROR: TIAGO_3 not found!")
    
    # Get API URL from controller args (optional)
    try:
        args = supervisor.getControllerArguments()
        api_url = (args[0] if isinstance(args, (list, tuple)) and args else args or DEFAULT_API) or DEFAULT_API
    except Exception:
        api_url = DEFAULT_API
    
    print(f"[position_tracker] API URL: {api_url}")
    print("[position_tracker] ===== STARTING POSITION TRACKING =====")
    
    update_counter = 0
    step_counter = 0
    
    while supervisor.step(timestep) != -1:
        step_counter += 1
        update_counter += 1
        
        # Update positions every ~100ms (instead of every timestep)
        if update_counter >= 12:  # Assuming 8ms timestep = ~100ms
            update_counter = 0
            
            # Debug: print that we're attempting to send
            if step_counter % 120 == 0:  # Every ~1 second
                print(f"[position_tracker] Heartbeat - step {step_counter}")
            
            # Get and send positions with orientation
            if tiago1:
                pos1 = tiago1.getPosition()
                rot1 = tiago1.getOrientation()  # Get 3x3 rotation matrix (as 9-element list)
                send_position_to_api(api_url, "1", pos1, rot1)
            
            if tiago2:
                pos2 = tiago2.getPosition()
                rot2 = tiago2.getOrientation()
                send_position_to_api(api_url, "2", pos2, rot2)
            
            if tiago3:
                pos3 = tiago3.getPosition()
                rot3 = tiago3.getOrientation()
                send_position_to_api(api_url, "3", pos3, rot3)


if __name__ == "__main__":
    main()