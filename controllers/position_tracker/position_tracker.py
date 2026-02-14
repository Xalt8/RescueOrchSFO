"""Position tracker supervisor - monitors all robot positions and sends to API."""

import json
import urllib.request
import urllib.error
import math
from controller import Supervisor

DEFAULT_API = "http://127.0.0.1:8000"


def rotation_matrix_to_euler(rotation_matrix):
    """Convert 3x3 rotation matrix to Euler angles (roll, pitch, yaw)."""
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
            "yaw": yaw
        }).encode("utf-8")
        
        url = f"{api_url}/tiago/{robot_id}/position"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            pass  # Silent success
            
    except urllib.error.URLError as e:
        pass  # Silent fail - don't spam console
    except OSError as e:
        pass


def poll_movements(api_url):
    """Poll for movement commands from API."""
    try:
        req = urllib.request.Request(f"{api_url}/supervisor/movements")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            return json.loads(resp.read().decode())
    except:
        return {}


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
    print("[position_tracker] ===== STARTING POSITION TRACKING AND MOVEMENT CONTROL =====")
    
    # Map robot IDs to robot objects
    robots = {"1": tiago1, "2": tiago2, "3": tiago3}
    
    update_counter = 0
    step_counter = 0
    active_movements = {}
    
    while supervisor.step(timestep) != -1:
        step_counter += 1
        update_counter += 1
        
        # Poll for new movement commands and send positions every ~100ms
        if update_counter >= 12:  # Assuming 8ms timestep = ~100ms
            update_counter = 0
            
            # Get new movement commands from API
            new_movements = poll_movements(api_url)
            for robot_id, movement_data in new_movements.items():
                if robot_id not in active_movements:
                    print(f"[position_tracker] 🎯 Starting movement: Robot {robot_id} → ({movement_data['x']:.2f}, {movement_data['y']:.2f})")
                active_movements[robot_id] = movement_data
            
            # Heartbeat
            if step_counter % 120 == 0:  # Every ~1 second
                print(f"[position_tracker] Heartbeat - step {step_counter}, active movements: {len(active_movements)}")
            
            # Send position updates to API
            if tiago1:
                pos1 = tiago1.getPosition()
                rot1 = tiago1.getOrientation()
                send_position_to_api(api_url, "1", pos1, rot1)
            
            if tiago2:
                pos2 = tiago2.getPosition()
                rot2 = tiago2.getOrientation()
                send_position_to_api(api_url, "2", pos2, rot2)
            
            if tiago3:
                pos3 = tiago3.getPosition()
                rot3 = tiago3.getOrientation()
                send_position_to_api(api_url, "3", pos3, rot3)
        
        # Update smooth movements EVERY timestep for smooth animation
        completed = []
        for robot_id, target_data in list(active_movements.items()):
            robot = robots.get(robot_id)
            if not robot:
                continue
            
            current_pos = robot.getPosition()
            tx, ty, tz = target_data['x'], target_data['y'], target_data['z']
            speed = target_data.get('speed', 2.5)
            
            # Calculate distance to target
            dx = tx - current_pos[0]
            dy = ty - current_pos[1]
            dz = tz - current_pos[2]
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            # SAFETY: If robot has gone way past target, stop immediately
            if distance > 15.0:
                print(f"[position_tracker] ⚠️ Robot {robot_id} too far from target ({distance:.1f}m) - stopping!")
                translation_field = robot.getField("translation")
                translation_field.setSFVec3f([tx, ty, tz])
                completed.append(robot_id)
                continue
            
            # Check if arrived (increased threshold to 0.2m for reliability)
            if distance < 0.2:
                translation_field = robot.getField("translation")
                translation_field.setSFVec3f([tx, ty, tz])
                completed.append(robot_id)
                print(f"[position_tracker] ✓ Robot {robot_id} arrived at target! (final distance: {distance:.2f}m)")
                continue
            
            # Calculate step size based on speed and timestep
            move_step = speed * (timestep / 1000.0)  # Convert ms to seconds
            
            # If step would overshoot target, just snap to final position
            if move_step >= distance:
                translation_field = robot.getField("translation")
                translation_field.setSFVec3f([tx, ty, tz])
                completed.append(robot_id)
                print(f"[position_tracker] ✓ Robot {robot_id} reached target!")
                continue
            
            # Move incrementally toward target (smooth animation)
            nx = current_pos[0] + (dx / distance) * move_step
            ny = current_pos[1] + (dy / distance) * move_step
            nz = current_pos[2] + (dz / distance) * move_step
            
            translation_field = robot.getField("translation")
            translation_field.setSFVec3f([nx, ny, nz])
        
        # Remove completed movements from active list
        for robot_id in completed:
            del active_movements[robot_id]


if __name__ == "__main__":
    main()