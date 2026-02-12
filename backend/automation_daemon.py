"""Simple automation daemon that drives robots via the backend HTTP API.

This script is intentionally minimal: it demonstrates how to call the
existing `/mavic` and `/tiago` routers. It's async and uses `httpx` so it
can be extended easily for concurrent missions or long-running tasks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, Union, Annotated, List, Type
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

import os

load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logger = logging.getLogger("automation_daemon")

# Global httpx client for backend API
_http_client: httpx.AsyncClient | None = None


async def get_http_client(base_url: str = "http://127.0.0.1:8000") -> httpx.AsyncClient:
    """Get or create a shared httpx async client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(base_url=base_url, timeout=10.0)
    return _http_client


async def close_http_client() -> None:
    """Close the global http client."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None


async def mavic_status() -> Any:
    """Get current Mavic drone status."""
    client = await get_http_client()
    r = await client.get("/mavic/status")
    r.raise_for_status()
    return r.json()


async def mavic_takeoff() -> Any:
    """Command Mavic to takeoff."""
    client = await get_http_client()
    r = await client.post("/mavic/takeoff")
    r.raise_for_status()
    return r.json()


async def mavic_land() -> Any:
    """Command Mavic to land."""
    client = await get_http_client()
    r = await client.post("/mavic/land")
    r.raise_for_status()
    return r.json()


async def mavic_set_altitude(altitude: float) -> Any:
    """Set target altitude for Mavic."""
    client = await get_http_client()
    r = await client.post("/mavic/altitude", json={"altitude": altitude})
    r.raise_for_status()
    return r.json()


async def tiago_status() -> Any:
    """Get current Tiago status."""
    client = await get_http_client()
    r = await client.get("/tiago/status")
    r.raise_for_status()
    return r.json()


async def tiago_stop() -> Any:
    """Command Tiago to stop."""
    client = await get_http_client()
    r = await client.post("/tiago/stop")
    r.raise_for_status()
    return r.json()



# Pydantic models for each robot function (used by LLM)

class MavicStatusCmd(BaseModel):
    """Get current Mavic drone status."""
    command: Literal["mavic_status"]


class MavicTakeoffCmd(BaseModel):
    """Command Mavic to takeoff."""
    command: Literal["mavic_takeoff"]


class MavicLandCmd(BaseModel):
    """Command Mavic to land."""
    command: Literal["mavic_land"]


class MavicSetAltitudeCmd(BaseModel):
    """Set target altitude for Mavic."""
    command: Literal["mavic_set_altitude"]
    altitude: float = Field(..., ge=0.0, le=50.0, description="Target altitude in meters (0-50m)")


class TiagoStatusCmd(BaseModel):
    """Get current Tiago robot status."""
    command: Literal["tiago_status"]


class TiagoStopCmd(BaseModel):
    """Command Tiago to stop."""
    command: Literal["tiago_stop"]


# Discriminated union of all available commands
RobotCommand = Annotated[
    Union[
        MavicStatusCmd,
        MavicTakeoffCmd,
        MavicLandCmd,
        MavicSetAltitudeCmd,
        TiagoStatusCmd,
        TiagoStopCmd,
    ],
    Field(discriminator="command"),
]


class OutputModel(BaseModel):
    """LLM output: sequence of robot commands to execute."""
    actions: list[RobotCommand] = Field(description="The sequence of commands to execute to reach the goal.")


client = genai.Client(api_key=GEMINI_API_KEY)


def run_robot_loop(
    goal: str,
    system_prompt: str,
    output_model: Type[BaseModel],
    client: genai.Client = client,
    model = "gemini-robotics-er-1.5-preview",
    ) -> Type[BaseModel] | None:

    response = client.models.generate_content(
    model=model,
    # Pass as a flat list: [ImagePart, PromptString]
    contents=[goal], 
    config=types.GenerateContentConfig(
        temperature=0.0,
        thinking_config=types.ThinkingConfig(thinking_budget=1024),
        response_mime_type="application/json",
        system_instruction=system_prompt,
        response_json_schema=output_model.model_json_schema())
    )
    try:
        validated_output = output_model.model_validate(response.parsed)
        return validated_output
    except Exception as e:
            print(f"LLM.invoke() error: {e}")
            return None


async def llm_based_mission(goal: str, 
                      system_prompt: str = None, 
                      output_model: Type[BaseModel] = OutputModel) -> None:
    """LLM-based control loop: given a high-level goal, use the LLM to generate and execute commands."""

    sys_prompt = system_prompt if system_prompt else """You are an autonomous robot controller.
When the user gives you a goal, respond with a sequence of commands to achieve that goal.

Available commands:
- mavic_status: Get current Mavic drone status
- mavic_takeoff: Command Mavic to takeoff
- mavic_land: Command Mavic to land
- mavic_set_altitude: Set target altitude for Mavic (in meters, 0-50m)
- tiago_status: Get current Tiago robot status
- tiago_stop: Command Tiago to stop

Return a valid JSON sequence of commands to accomplish the goal.
"""
    
    plan = run_robot_loop(goal=goal, system_prompt=sys_prompt, output_model=output_model)
    if plan is None:
        logger.error("Failed to generate a mission plan.")
        return
    if not isinstance(plan, OutputModel):
        logger.error("Invalid mission plan format.")
        return
    
    for i, action in enumerate(plan.actions):
        try:
            logger.info(f"Executing action {i+1}: {action.command}")
            
            # Dispatch to appropriate function based on command type
            if isinstance(action, MavicStatusCmd):
                result = await mavic_status()
            elif isinstance(action, MavicTakeoffCmd):
                result = await mavic_takeoff()
            elif isinstance(action, MavicLandCmd):
                result = await mavic_land()
            elif isinstance(action, MavicSetAltitudeCmd):
                result = await mavic_set_altitude(action.altitude)
            elif isinstance(action, TiagoStatusCmd):
                result = await tiago_status()
            elif isinstance(action, TiagoStopCmd):
                result = await tiago_stop()
            else:
                logger.warning(f"Unknown command: {action.command}")
                continue
            
            logger.info(f"  Result: {result}")
            await asyncio.sleep(0.5)  # Small delay between commands
        except Exception as e:
            logger.error(f"Error executing {action.command}: {e}")
            break


async def simple_mission() -> None:
    """Example mission: takeoff, ascend, hover, then land."""
    logger.info("Checking initial statuses")
    mavic_s = await mavic_status()
    logger.info("Mavic status: %s", mavic_s)
    tiago_s = await tiago_status()
    logger.info("Tiago status: %s", tiago_s)

    logger.info("Sending takeoff")
    await mavic_takeoff()
    await asyncio.sleep(1.0)

    logger.info("Set altitude to 2.0m")
    await mavic_set_altitude(2.0)
    await asyncio.sleep(2.0)

    logger.info("Hovering (sleeping for 5s)")
    await asyncio.sleep(5.0)

    logger.info("Landing")
    await mavic_land()

    logger.info("Stopping Tiago (safety)")
    await tiago_stop()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        # await simple_mission()
        print("Starting LLM-based mission...")
        await llm_based_mission(goal="Take off, ascend to 2m, hover for 5 seconds, then land.")
    except Exception as e:
        logger.exception("Mission failed: %s", e)
    finally:
        await close_http_client()


if __name__ == "__main__":
    asyncio.run(main())
    
