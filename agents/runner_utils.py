"""
Runner utilities
-----------------
ADK agents aren't called directly with agent.run(text) — you invoke them
through a Runner backed by a SessionService, which streams back Events.
This wraps that boilerplate once so each agent module can call a plain
run_agent(agent, prompt) -> str instead of repeating Runner/session setup
five times across the pipeline.

Reference: google.adk.runners.Runner, google.adk.sessions.InMemorySessionService
"""

import asyncio
import json
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

_session_service = InMemorySessionService()
_APP_NAME = "civic-triage-agent"


async def _run_agent_async(agent, prompt: str, user_id: str = "local-user") -> str:
    max_retries = 5
    delays = [4.0, 8.0, 16.0, 32.0, 60.0]
    for attempt in range(max_retries + 1):
        try:
            session_id = str(uuid.uuid4())
            await _session_service.create_session(
                app_name=_APP_NAME, user_id=user_id, session_id=session_id
            )
            runner = Runner(agent=agent, app_name=_APP_NAME, session_service=_session_service)

            final_text = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user", parts=[types.Part.from_text(text=prompt)]
                ),
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text += part.text

            return final_text
        except Exception as e:
            err_str = str(e)
            is_transient = any(
                term in err_str for term in [
                    "Quota exceeded", "RESOURCE_EXHAUSTED", "429",
                    "UNAVAILABLE", "503", "Service Unavailable"
                ]
            )
            if is_transient and attempt < max_retries:
                delay = delays[attempt]
                print(f"[runner_utils] Transient error (attempt {attempt+1}/{max_retries}), retrying in {delay:.0f}s...")
                await asyncio.sleep(delay)
            else:
                if is_transient:
                    print(f"[runner_utils] Giving up after {max_retries} attempts, raising to caller.")
                raise e


def run_agent(agent, prompt: str) -> str:
    """Synchronous convenience wrapper — call this from each agent's
    orchestrator-facing function so the rest of the pipeline stays sync."""
    return asyncio.run(_run_agent_async(agent, prompt))


async def _run_agent_multimodal_async(
    agent, text_prompt: str, image_bytes: bytes, mime_type: str, user_id: str = "local-user"
) -> str:
    max_retries = 5
    delays = [4.0, 8.0, 16.0, 32.0, 60.0]
    for attempt in range(max_retries + 1):
        try:
            session_id = str(uuid.uuid4())
            await _session_service.create_session(
                app_name=_APP_NAME, user_id=user_id, session_id=session_id
            )
            runner = Runner(agent=agent, app_name=_APP_NAME, session_service=_session_service)

            final_text = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        types.Part.from_text(text=text_prompt),
                    ],
                ),
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text += part.text

            return final_text
        except Exception as e:
            err_str = str(e)
            is_transient = any(
                term in err_str for term in [
                    "Quota exceeded", "RESOURCE_EXHAUSTED", "429",
                    "UNAVAILABLE", "503", "Service Unavailable"
                ]
            )
            if is_transient and attempt < max_retries:
                delay = delays[attempt]
                print(f"[runner_utils] Transient error (attempt {attempt+1}/{max_retries}), retrying in {delay:.0f}s...")
                await asyncio.sleep(delay)
            else:
                if is_transient:
                    print(f"[runner_utils] Giving up after {max_retries} attempts, raising to caller.")
                raise e


def run_agent_multimodal(
    agent, text_prompt: str, image_bytes: bytes, mime_type: str
) -> str:
    """Synchronous convenience wrapper for multimodal agent calls."""
    return asyncio.run(_run_agent_multimodal_async(agent, text_prompt, image_bytes, mime_type))



def parse_json_response(raw_text: str) -> dict:
    """
    Models often wrap JSON in ```json fences even when told not to.
    Strip those defensively before parsing rather than trusting the
    instruction alone.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())
