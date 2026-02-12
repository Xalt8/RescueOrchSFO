"""Simple automation daemon that drives robots via the backend HTTP API.

This script is intentionally minimal: it demonstrates how to call the
existing `/mavic` and `/tiago` routers. It's async and uses `httpx` so it
can be extended easily for concurrent missions or long-running tasks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, Union, Annotated, List, Type, Callable
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



client = genai.Client(api_key=GEMINI_API_KEY)


async def simple_mission(system_prompt: str, 
                   user_prompt: str,
                   tool_list: list[Callable[..., Any]],
                   CLIENT: genai.Client = client
                   ) -> None:

    available_functions = {fn.__name__: fn for fn in tool_list}

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=tool_list,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode='ANY')
        )    
    )   
    chat = client.chats.create(model="gemini-2.0-flash", config=config)
    response = chat.send_message(user_prompt) 

    max_steps = 10
    step = 0

    while response.function_calls and step < max_steps:
        step += 1
        tool_responses = []

        for fn in response.function_calls:
            # Find the actual function in our map
            function_to_call = available_functions.get(fn.name)
            
            if function_to_call:
                print(f"Executing: {fn.name} with args {fn.args}")
                
                # Await the async function call
                result = await function_to_call(**fn.args) 
                print(f"Result: {result}")

                tool_responses.append(types.Part.from_function_response(
                    name=fn.name,
                    response=result
                ))
            
        response = chat.send_message(tool_responses)
    
    if step >= max_steps:
        print("Aborting: exceeded max tool call steps.")

    print("Model has no more functions to call.")
    if response.text:
        print(f"Final response: {response.text}")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        tool_list = [mavic_takeoff, 
                    mavic_land, 
                    mavic_set_altitude]

        system_prompt = """You are an expert drone operator. 
        Use the available tools to control the Mavic drone and achieve the user's goal.
        Once the goal is achieved, stop calling functions and respond with a final message."""
        user_prompt = "Take off, ascend to 2m, hover for 5 seconds, then land."

        print("Starting LLM-based mission...")

        await simple_mission(system_prompt=system_prompt, 
                    user_prompt=user_prompt, 
                    tool_list=tool_list)

        print("done with mission.")    
        
        # await llm_based_mission(goal="Take off, ascend to 2m, hover for 5 seconds, then land.")
    except Exception as e:
        logger.exception("Mission failed: %s", e)
    finally:
        await close_http_client()


if __name__ == "__main__":
    asyncio.run(main())

    

    
