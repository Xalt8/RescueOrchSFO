import httpx
import asyncio
import math
from google import genai
from dotenv import load_dotenv
from google.genai import types

import os

load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DEFAULT_API = "http://127.0.0.1:8000"

def get_object_position_position(position: list[float]) -> dict:
    """Get current object position."""
    position [0] = position [0] - 1.5 
    return {"position": position}


async def get_tiago_status(robot_id: str = "1"):
    """Get current status of a specific Tiago robot."""
    async with httpx.AsyncClient() as client:
        # response = await client.get(f"{DEFAULT_API}/{robot_id}/status")
        response = await client.get(f"{DEFAULT_API}/tiago/{robot_id}/status")
        response.raise_for_status()
        return response.json()


async def get_all_tiago_status(robot_ids:list[str]=["1", "2", "3"]):
    """Get status of all Tiago robots concurrently."""

    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"{DEFAULT_API}/tiago/{rid}/status")
            for rid in robot_ids
        ]
        responses = await asyncio.gather(*tasks)  # run concurrently

        # Convert responses to JSON and map to robot IDs
        return {robot_ids[i]: responses[i].json() for i in range(len(robot_ids))}


async def move_tiago(robot_id: str, velocity: dict):
    """Command a specific Tiago robot to move with given velocity."""
    
    # DEBUG: Print what we're about to send
    print(f"[DEBUG] Calling /tiago/{robot_id}/velocity with: {velocity}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DEFAULT_API}/tiago/{robot_id}/velocity", 
                json=velocity
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] HTTP {e.response.status_code}")
            print(f"  Response body: {e.response.text}")
            print(f"  Sent: {velocity}")
            raise


async def stop_robot(robot_id: str) -> dict:
    """
    Stop a robot immediately.
    
    Args:
        robot_id: Which robot to stop
    
    Returns:
        dict with status
    """
    print(f"[stop_robot] Stopping robot {robot_id}")
    velocity = {"linear_x": 0.0, "linear_y": 0.0, "angular": 0.0}
    result = await move_tiago(robot_id, velocity)
    return {"success": True, "robot_id": robot_id}



async def wait_for_movement_complete(
    robot_id: str,
    target_x: float,
    target_y: float,
    threshold: float = 0.2,
    timeout: float = 30.0,
    check_interval: float = 0.5
    ) -> dict:
    """
    Wait for robot to reach target position (or timeout).
    
    Args:
        robot_id: Robot identifier
        target_x, target_y: Target coordinates
        threshold: Distance threshold to consider "arrived" (meters)
        timeout: Maximum time to wait (seconds)
        check_interval: How often to check position (seconds)
    
    Returns:
        dict with success status and final position
    """
    start_time = asyncio.get_event_loop().time()
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        
        if elapsed > timeout:
            status = await get_tiago_status(robot_id)
            return {
                "success": False,
                "reason": "timeout",
                "final_position": status.get("position"),
                "elapsed_time": elapsed
            }
        
        # Get current position
        status = await get_tiago_status(robot_id)
        current_pos = status.get("position")
        
        if not current_pos:
            await asyncio.sleep(check_interval)
            continue
        
        # Calculate distance to target
        dx = current_pos["x"] - target_x
        dy = current_pos["y"] - target_y
        distance = math.sqrt(dx**2 + dy**2)
        
        print(f"[Robot {robot_id}] Distance to target: {distance:.2f}m")
        
        if distance < threshold:
            return {
                "success": True,
                "final_position": current_pos,
                "elapsed_time": elapsed
            }
        
        await asyncio.sleep(check_interval)


async def move_robot_to_position(
    robot_id: str,
    target_x: float,
    target_y: float,
    speed: float = 0.5  # Increased default speed
) -> dict:
    """
    Simple demo movement - just move toward target with basic correction.
    """
    print(f"[move_robot_to_position] Moving robot {robot_id} to ({target_x}, {target_y})")
    
    # Get current position
    status = await get_tiago_status(robot_id)
    current_pos = status.get("position")
    
    if not current_pos:
        return {"success": False, "error": "Could not get position"}
    
    timeout = 60.0  # Reduced timeout
    threshold = 0.5  # Larger threshold - easier to reach
    start_time = asyncio.get_event_loop().time()
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        
        if elapsed > timeout:
            await move_tiago(robot_id, {"linear_x": 0.0, "linear_y": 0.0, "angular": 0.0})
            return {"success": False, "reason": "timeout"}
        
        # Get current position
        status = await get_tiago_status(robot_id)
        current_pos = status.get("position")
        if not current_pos:
            await asyncio.sleep(0.2)
            continue
        
        # Calculate distance and angle
        dx = target_x - current_pos["x"]
        dy = target_y - current_pos["y"]
        distance = math.sqrt(dx**2 + dy**2)
        
        # Check if arrived
        if distance < threshold:
            await move_tiago(robot_id, {"linear_x": 0.0, "linear_y": 0.0, "angular": 0.0})
            print(f"[Robot {robot_id}] ✓ Arrived!")
            return {"success": True, "elapsed_time": elapsed}
        
        # Simple control: point toward target and drive
        target_angle = math.atan2(dy, dx)
        current_yaw = current_pos.get("yaw", 0) or 0
        
        heading_error = target_angle - current_yaw
        # Normalize to [-π, π]
        while heading_error > math.pi:
            heading_error -= 2 * math.pi
        while heading_error < -math.pi:
            heading_error += 2 * math.pi
        
        # Fast turning
        angular_vel = 5.0 * heading_error  # High gain for fast turning
        angular_vel = max(-3.0, min(3.0, angular_vel))  # High limit
        
        # Always move forward (even while turning)
        linear_vel = speed if abs(heading_error) < math.radians(45) else speed * 0.5
        
        await move_tiago(robot_id, {
            "linear_x": linear_vel,
            "linear_y": 0.0,
            "angular": angular_vel
        })
        
        if int(elapsed * 5) % 10 == 0:  # Print occasionally
            print(f"[Robot {robot_id}] {distance:.1f}m away, heading error: {math.degrees(heading_error):.0f}°")
        
        await asyncio.sleep(0.1)  # Fast update rate


async def move_robot_supervisor(
    robot_id: str,
    target_x: float,
    target_y: float,
    speed: float = 2.5
) -> dict:
    """Move robot using supervisor - fire and forget with estimated time."""
    
    # Get current position to estimate time
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DEFAULT_API}/tiago/{robot_id}/status")
        status = response.json()
        current_pos = status.get("position")
    
    if not current_pos:
        return {"success": False, "error": "Could not get position"}
    
    # Calculate travel time
    dx = target_x - current_pos["x"]
    dy = target_y - current_pos["y"]
    distance = math.sqrt(dx**2 + dy**2)
    travel_time = (distance / speed) + 1.0  # Add 1 second buffer
    
    print(f"[Robot {robot_id}] Moving {distance:.1f}m to ({target_x:.2f}, {target_y:.2f})")
    print(f"[Robot {robot_id}] Estimated time: {travel_time:.1f}s")
    
    # Send movement command
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{DEFAULT_API}/supervisor/move",
            json={
                "robot_id": robot_id,
                "target": {"x": target_x, "y": target_y, "z": 0.095},
                "speed": speed
            }
        )
    
    # Wait estimated time + buffer
    await asyncio.sleep(travel_time)
    
    print(f"[Robot {robot_id}] ✓ Movement complete")
    return {"success": True, "estimated_time": travel_time}


async def get_robot_location(robot_id: str) -> dict:
    """
    Get current location of a robot.
    
    Args:
        robot_id: Which robot to query ("1", "2", or "3")
    
    Returns:
        dict with position data
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DEFAULT_API}/tiago/{robot_id}/status")
        status = response.json()
    
    position = status.get("position")
    
    if position:
        return {
            "robot_id": robot_id,
            "x": position["x"],
            "y": position["y"],
            "z": position.get("z", 0.095)
        }
    else:
        return {
            "robot_id": robot_id,
            "error": "Position not available"
        }


system_prompt = """You are a robot controller. You MUST complete movement tasks.
    TOOLS:
    - get_robot_location(robot_id): Get position
    - move_robot_supervisor(robot_id, target_x, target_y, speed): MOVE ROBOT (required to complete tasks!)
    - get_door_position(): Get door coordinates

    CRITICAL:
    Getting robot locations is NOT completing the task!
    You MUST call move_robot_supervisor to actually move robots!

    WORKFLOW for "send robot to X":
    1. get_robot_location for all robots (ONCE per robot)
    2. Calculate which is closest
    3. IMMEDIATELY call move_robot_supervisor to move it
    4. STOP - do not keep checking locations

    If you only get locations without moving, you FAIL the task."""



client = genai.Client(api_key=GEMINI_API_KEY)


async def llm_controlled_mission(
    user_prompt: str,
    system_prompt: str = system_prompt,
    client: genai.Client = client,
    max_turns: int = 5
    ) -> None:
    """
    Multi-turn LLM execution - keeps calling until task is complete.
    """
    tool_list = [
        move_robot_supervisor,
        get_robot_location,
        stop_robot,
    ]

    available_functions = {fn.__name__: fn for fn in tool_list}

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=tool_list,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode='ANY')
        )
    )

    print("\n" + "="*60)
    print("MISSION EXECUTION")
    print("="*60)

    # Start conversation
    messages = [user_prompt]
    
    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")
        
        # Call LLM with current messages
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=messages,
            config=config
        )

        # Check if LLM wants to call functions
        if not response.function_calls:
            print("No more function calls - task complete")
            if response.text:
                print(f"Final response: {response.text}")
            break

        # Execute all function calls
        tool_results = []
        for fn in response.function_calls:
            function_to_call = available_functions.get(fn.name)

            if not function_to_call:
                print(f"Unknown function: {fn.name}")
                continue

            print(f"\nExecuting: {fn.name}")
            print(f"  Arguments: {fn.args}")

            try:
                result = await function_to_call(**fn.args)
                print(f"  ✓ Result: {result}")

                tool_results.append(
                    types.Part.from_function_response(
                        name=fn.name,
                        response=result
                    )
                )

            except Exception as e:
                print(f"  ✗ Error: {e}")
                tool_results.append(
                    types.Part.from_function_response(
                        name=fn.name,
                        response={"error": str(e)}
                    )
                )

        # Add results to conversation
        messages.append(tool_results)

    print("\n" + "="*60)
    print("Mission Complete!")
    print("="*60)


async def main():
    door_position = get_object_position_position(position=[7.75, -1.45, 0.0]).get("position")
    window_position = get_object_position_position(position=[7.75, 0.45, 0.0]).get("position") 
    manhole_position = get_object_position_position(position=[0, 0, 0.0]).get("position")

    to_window_prompt = f"Task: Move robot 1 to position {window_position}"
    await llm_controlled_mission(user_prompt=to_window_prompt)

    to_door_prompt = f"Task: Move robot 3 to position {door_position}"
    await llm_controlled_mission(user_prompt=to_door_prompt)


if __name__ == "__main__":
    asyncio.run(main())    
    
