import asyncio

from google.adk.agents.context import Context
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import Workflow, FunctionNode, START
from google.genai import types

from processor.adk.workflow import (
    validate_evidence,
    deterministic_analysis,
     run_gemini_investigator,
)


FIXTURE_EVIDENCE = {
    "incident_id": "INC-001",
    "correlation_id": "CORR-001",

    "agent_execution": {
        "incident_id": "INC-001",
        "correlation_id": "CORR-001",
        "events": [
            {
                "sequence_number": 1,
                "timestamp": "2026-09-01T10:00:00+00:00",
                "source": "USER",
                "event_type": "USER_REQUEST",
                "actor": "USER",
                "action": "UPDATE_ACCOUNT",
                "status": "RECEIVED",
                "details": "Update requested",
            },
        ],
        "provenance": {
            "database": "BigQuery",
            "dataset": "patchamomma",
            "view": "agent_execution_events",
        },
    },

    "tool_execution": {
        "incident_id": "INC-001",
        "correlation_id": "CORR-001",
        "executions": [
            {
                "execution_id": "EXEC-001",
                "incident_id": "INC-001",
                "correlation_id": "CORR-001",
                "started_at": "2026-09-01T10:00:01+00:00",
                "completed_at": "2026-09-01T10:00:02+00:00",
                "tool_name": "account_update",
                "request": {
                    "account_id": "ACC-001"
                },
                "response": {
                    "status": "success"
                },
                "status": "SUCCESS",
                "duration_ms": 1000,
                "error_details": None,
            }
        ],
        "execution_count": 1,
        "provenance": {
            "database": "AlloyDB",
            "instance": "primary",
            "cluster": "patchamomma-alloydb",
            "database_name": "postgres",
            "table": "tool_execution",
        },
    },

    "authoritative_state": {
        "incident_id": "INC-001",
        "correlation_id": "CORR-001",
        "state_available": True,
        "state": {
            "authoritative_status": "UNCHANGED",
        },
        "provenance": {
            "database": "Spanner",
            "instance": "patchamomma-v2",
            "database_name": "patchamomma",
            "table": "account_state",
        },
    },

    "runtime_telemetry": {
        "incident_id": "INC-001",
        "correlation_id": "CORR-001",
        "events": [
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": "EXEC-001",
                "retry_count": "0",
            }
        ],
        "provenance": {
            "database": "Bigtable",
            "instance": "patchamomma-v2",
            "table": "runtime_telemetry",
            "column_family": "telemetry",
        },
    },
}


def collect_fixture_evidence(ctx: Context) -> dict:
    """Inject deterministic fixture evidence into ADK state."""

    incident_id = ctx.state["incident_id"]

    assert incident_id == "INC-001"

    ctx.state["evidence"] = FIXTURE_EVIDENCE

    return {
        "incident_id": incident_id,
        "evidence_loaded": True,
    }


collect_fixture_node = FunctionNode(
    func=collect_fixture_evidence,
    name="collect_fixture_evidence",
)


validate_evidence_node = FunctionNode(
    func=validate_evidence,
    name="validate_evidence",
)


deterministic_analysis_node = FunctionNode(
    func=deterministic_analysis,
    name="deterministic_analysis",
)

gemini_investigator_node = FunctionNode(
    func=run_gemini_investigator,
    name="run_gemini_investigator",
    rerun_on_resume=True,
)

test_workflow = Workflow(
    name="patchamomma_fixture_workflow",
    description=(
        "Fixture-based test of the Patchamomma ADK workflow "
        "without AlloyDB connectivity."
    ),
    edges=[
        (START, collect_fixture_node),
        (collect_fixture_node, validate_evidence_node),
        (validate_evidence_node, deterministic_analysis_node),
        (deterministic_analysis_node, gemini_investigator_node),
    ],
)


async def main():
    session_service = InMemorySessionService()

    await session_service.create_session(
        app_name="patchamomma",
        user_id="workflow-test-user",
        session_id="workflow-test-session",
        state={
            "incident_id": "INC-001",
        },
    )

    runner = Runner(
        agent=test_workflow,
        app_name="patchamomma",
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[
            types.Part(
                text="Investigate incident INC-001."
            )
        ],
    )

    print("\n=== PATCHAMOMMA ADK WORKFLOW TEST ===")
    print("Incident: INC-001")
    print("Using fixture evidence (AlloyDB bypassed)\n")

    async for event in runner.run_async(
        user_id="workflow-test-user",
        session_id="workflow-test-session",
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

    session = await session_service.get_session(
        app_name="patchamomma",
        user_id="workflow-test-user",
        session_id="workflow-test-session",
    )

    final_state = session.state

    print("\n=== WORKFLOW TEST COMPLETE ===")

    print("\nEvidence validated:")
    print(final_state.get("evidence_validated"))

    findings = final_state.get("deterministic_findings") or {}

    print("\nOutcome:")
    print(findings.get("outcome_confirmation"))

    print("\nConflicts:")
    for conflict in findings.get("conflicts", []):
        print(f"  - {conflict['type']}")
    gemini_result = final_state.get("gemini_investigation")

    print("\nGemini investigation:")
    print(gemini_result)
    
    print("\nExpected:")
    print("  Evidence validated: True")
    print("  Outcome: UNCHANGED")
    print("  Conflict: TOOL_SUCCESS_VS_STATE_UNCHANGED")


if __name__ == "__main__":
    asyncio.run(main())