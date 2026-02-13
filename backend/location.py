import httpx
import asyncio

DEFAULT_API = "http://127.0.0.1:8000"

async def get_door_position():
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



if __name__ == "__main__":
    
    
    robot_status = asyncio.run(get_all_tiago_status())
    print(robot_status)

    door_loc = asyncio.run(get_door_position())
    print(door_loc)