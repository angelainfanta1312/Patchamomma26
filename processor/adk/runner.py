import asyncio
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from processor.adk.workflow import patchamomma_workflow


APP_NAME = "patchamomma"
USER_ID = "patchamomma"


async def investigate_incident_async(
    incident_id: str,
    workflow=None,
) -> dict[str, Any]:

    session_service = InMemorySessionService()

    session_id = f"investigation-{incident_id}"

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
        state={
            "incident_id": incident_id,
        },
    )

    workflow = workflow or patchamomma_workflow

    runner = Runner(
        agent=workflow,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"Investigate incident {incident_id}.",
            )
        ],
    )

    async for _ in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        pass

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    if session is None:
        raise RuntimeError(
            f"ADK session not found after investigation: {session_id}"
        )

    state = session.state

    return {
        "incident_id": incident_id,
        "evidence": state.get("evidence"),
        "evidence_validated": state.get("evidence_validated"),
        "deterministic_findings": state.get(
            "deterministic_findings"
        ),
        "gemini_investigation": state.get(
            "gemini_investigation"
        ),
    }


def investigate_incident(
    incident_id: str,
) -> dict[str, Any]:
    return asyncio.run(
        investigate_incident_async(incident_id)
    )