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

def get_door_position():
    """Get current door position."""
    return {"position": [7.75, -1.45, 0.0]}


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
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{DEFAULT_API}/tiago/{robot_id}/velocity", json=velocity)
        response.raise_for_status()
        return response.json()


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


async def get_robot_location(robot_id: str) -> dict:
    """
    Get current location of a robot.
    
    Args:
        robot_id: Which robot to query
    
    Returns:
        dict with position data
    """
    status = await get_tiago_status(robot_id)
    position = status.get("position")
    
    if position:
        return {
            "robot_id": robot_id,
            "x": position["x"],
            "y": position["y"],
            "z": position["z"]
        }
    else:
        return {
            "robot_id": robot_id,
            "error": "Position not available"
        }


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
    speed: float = 0.3
) -> dict:
    """
    Move robot using simple pursuit - turn toward target while moving.
    """
    print(f"[move_robot_to_position] Moving robot {robot_id} to ({target_x}, {target_y})")
    
    # Get current position with retry
    max_retries = 5
    current_pos = None
    for attempt in range(max_retries):
        status = await get_tiago_status(robot_id)
        current_pos = status.get("position")
        if current_pos:
            break
        print(f"[Robot {robot_id}] Waiting for position data... (attempt {attempt + 1}/{max_retries})")
        await asyncio.sleep(0.5)
    
    if not current_pos:
        return {
            "success": False,
            "error": "Could not get robot position",
            "robot_id": robot_id
        }
    
    timeout = 60.0
    check_interval = 0.2
    threshold = 0.3
    start_time = asyncio.get_event_loop().time()
    
    # Calculate initial direction
    dx = target_x - current_pos["x"]
    dy = target_y - current_pos["y"]
    distance = math.sqrt(dx**2 + dy**2)
    
    if distance < threshold:
        return {
            "success": True,
            "message": "Already at target",
            "distance": distance
        }
    
    target_angle = math.atan2(dy, dx)
    
    # Phase 1: Initial turn
    print(f"[Robot {robot_id}] Phase 1: Turning toward target (angle: {math.degrees(target_angle):.1f}°)...")
    turn_time = min(3.0, abs(target_angle) * 2)  # Turn longer for larger angles
    turn_start = asyncio.get_event_loop().time()
    
    angular_vel = 0.5 if target_angle > 0 else -0.5
    
    await move_tiago(robot_id, {
        "linear_x": 0.0,
        "linear_y": 0.0,
        "angular": angular_vel
    })
    
    while asyncio.get_event_loop().time() - turn_start < turn_time:
        await asyncio.sleep(0.1)
    
    # Phase 2: Move forward with course correction
    print(f"[Robot {robot_id}] Phase 2: Moving forward...")
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            await move_tiago(robot_id, {"linear_x": 0.0, "linear_y": 0.0, "angular": 0.0})
            return {"success": False, "reason": "timeout", "elapsed_time": elapsed}
        
        status = await get_tiago_status(robot_id)
        current_pos = status.get("position")
        
        if not current_pos:
            await asyncio.sleep(check_interval)
            continue
        
        dx = target_x - current_pos["x"]
        dy = target_y - current_pos["y"]
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance < threshold:
            await move_tiago(robot_id, {"linear_x": 0.0, "linear_y": 0.0, "angular": 0.0})
            print(f"[Robot {robot_id}] ✓ Arrived at target!")
            return {"success": True, "final_position": current_pos, "elapsed_time": elapsed}
        
        # Calculate target angle
        target_angle = math.atan2(dy, dx)
        
        # Proportional control
        K_angular = 0.8
        angular_vel = K_angular * target_angle
        angular_vel = max(-1.0, min(1.0, angular_vel))
        
        # Adjust speed based on heading error
        if abs(target_angle) > math.radians(30):
            linear_vel = speed * 0.3  # Go slow when off-course
        else:
            linear_vel = min(speed, distance * 0.5)
        
        await move_tiago(robot_id, {
            "linear_x": linear_vel,
            "linear_y": 0.0,
            "angular": angular_vel
        })
        
        if int(elapsed / 2) % 3 == 0:
            print(f"[Robot {robot_id}] Dist: {distance:.2f}m, heading error: {math.degrees(target_angle):.1f}°")
        
        await asyncio.sleep(check_interval)


async def llm_controlled_mission(
    system_prompt: str,
    user_prompt: str,
    client: genai.Client,
    max_steps: int = 20
) -> None:
    """
    Run a mission where the LLM controls robots with proper waiting for movement.
    
    The LLM has access to:
    - move_robot_to_position: Move robot to coordinates and wait until arrived
    - get_robot_location: Get current robot position
    - stop_robot: Stop a robot
    - get_door_position: Get door location
    
    Example usage:
        system_prompt = '''You are a robot mission controller. 
        You have 3 Tiago robots at your command.
        Use move_robot_to_position to send robots to locations.
        The function will automatically wait for the robot to arrive.'''
        
        user_prompt = "Send robot 1 to the door, then send robot 2 to position (5, 5)"
    """
    
    # Tools available to the LLM
    tool_list = [
        move_robot_to_position,
        get_robot_location,
        stop_robot,
        get_door_position,
    ]
    
    available_functions = {fn.__name__: fn for fn in tool_list}
    
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=tool_list,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode='ANY')
        )
    )
    
    chat = client.chats.create(model="gemini-2.0-flash", config=config)
    response = chat.send_message(user_prompt)
    
    step = 0
    
    while response.function_calls and step < max_steps:
        step += 1
        print(f"\n{'='*60}")
        print(f"STEP {step}/{max_steps}")
        print(f"{'='*60}")
        
        tool_responses = []
        
        for fn in response.function_calls:
            function_to_call = available_functions.get(fn.name)
            
            if function_to_call:
                print(f"\nLLM wants to call: {fn.name}")
                print(f"Arguments: {fn.args}")
                
                # Execute the function (this will WAIT if it's a movement function)
                try:
                    result = await function_to_call(**fn.args)
                    print(f"Result: {result}")
                    
                    tool_responses.append(types.Part.from_function_response(
                        name=fn.name,
                        response=result
                    ))
                except Exception as e:
                    print(f"Error: {e}")
                    tool_responses.append(types.Part.from_function_response(
                        name=fn.name,
                        response={"error": str(e)}
                    ))
            else:
                print(f"Unknown function: {fn.name}")
        
        # Send results back to LLM for next decision
        response = chat.send_message(tool_responses)
    
    if step >= max_steps:
        print("\n Aborting: exceeded max tool call steps.")
    
    print("\n" + "="*60)
    print("Mission complete!")
    print("="*60)
    
    if response.text:
        print(f"\nFinal LLM response:\n{response.text}")




if __name__ == "__main__":
    
    
    system_prompt = """You are a robot mission controller for a rescue operation.
    
    You control 3 Tiago++ robots (IDs: "1", "2", "3").
    
    Available functions:
    - move_robot_to_position(robot_id, target_x, target_y, speed): Move robot to coordinates. This function WAITS until the robot arrives.
    - get_robot_location(robot_id): Get current position of a robot
    - stop_robot(robot_id): Stop a robot immediately
    - get_door_position(): Get the coordinates of the door
    
    When moving robots:
    1. Check their current position first
    2. Use move_robot_to_position - it will automatically wait for arrival
    3. You can then proceed with the next command
    
    Be efficient and clear in your actions."""
    

    door_position = get_door_position()
    target_location = door_position.get("position", [7.75, -1.45, 0.0])  # Default to known door position if API fails

    user_prompt = f"""
    Mission: Send robot 1 to the position {target_location}.
    """

    user_prompt = user_prompt.format(target_location=target_location)
    
    client = genai.Client(api_key=GEMINI_API_KEY)

    asyncio.run(llm_controlled_mission(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        client=client
    ))
