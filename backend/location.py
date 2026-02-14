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


async def llm_controlled_mission(
    system_prompt: str,
    user_prompt: str,
    client: genai.Client,
) -> None:
    """
    The LLM must output ALL required tool calls in a single response.
    Movement functions already wait until completion.
    """

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
            disable=True  # We manually execute
        ),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode='ANY')
        )
    )

    # Single LLM call
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_prompt,
        config=config
    )

    print("\n" + "="*60)
    print("MISSION EXECUTION")
    print("="*60)

    if not response.function_calls:
        print("No tool calls returned by LLM.")
        if response.text:
            print(response.text)
        return

    tool_results = []

    # Execute ALL tool calls sequentially
    for fn in response.function_calls:
        function_to_call = available_functions.get(fn.name)

        if not function_to_call:
            print(f"Unknown function: {fn.name}")
            continue

        print(f"\nExecuting: {fn.name}")
        print(f"Arguments: {fn.args}")

        try:
            result = await function_to_call(**fn.args)
            print(f"Result: {result}")

            tool_results.append(
                types.Part.from_function_response(
                    name=fn.name,
                    response=result
                )
            )

        except Exception as e:
            print(f"Error: {e}")
            tool_results.append(
                types.Part.from_function_response(
                    name=fn.name,
                    response={"error": str(e)}
                )
            )

    # Optional: one final LLM call for summary
    final_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=tool_results
    )

    print("\n" + "="*60)
    print("Mission complete!")
    print("="*60)

    if final_response.text:
        print(f"\nFinal LLM response:\n{final_response.text}")



if __name__ == "__main__":
    
    
    system_prompt = """You are a robot mission controller for a rescue operation.
    
    You control 3 Tiago++ robots (IDs: "1", "2", "3").
    
    Available functions:
    - move_robot_to_position(robot_id, target_x, target_y, speed): Move robot to coordinates. This function WAITS until the robot arrives.
    - get_robot_location(robot_id): Get current position of a robot
    - stop_robot(robot_id): Stop a robot immediately
    - get_door_position(): Get the coordinates of the door

    IMPORTANT:
    - Generate the COMPLETE mission plan in a single response.
    - Assume movement functions block until arrival.
    - Do NOT request intermediate state checks.
    - Call all required functions in order in one response.
    """
    

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
