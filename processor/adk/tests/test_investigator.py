import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from processor.adk.investigator import patchamomma_investigator


APP_NAME = "patchamomma"
USER_ID = "adk-test-user"
SESSION_ID = "adk-test-session"


async def main():
    session_service = InMemorySessionService()

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    runner = Runner(
        agent=patchamomma_investigator,
        app_name=APP_NAME,
        session_service=session_service,
    )

    prompt = """
Investigate incident INC-001.

Retrieve all available evidence using your tools.
Cross-check the agent execution, tool execution,
authoritative business state, and runtime telemetry.

Do not infer beyond the evidence.
"""

    content = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    print("\n=== PATCHAMOMMA ADK INVESTIGATOR TEST ===")
    print("Incident: INC-001")
    print("Starting ADK investigation...\n")

    final_response = None

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        print(
            f"[EVENT] "
            f"author={event.author} "
            f"type={type(event).__name__}"
        )

        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)

        if event.is_final_response():
            final_response = event

    print("\n=== FINAL ADK RESPONSE ===")

    if final_response and final_response.content:
        for part in final_response.content.parts:
            if part.text:
                print(part.text)

    print("\n=== ADK TEST COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())