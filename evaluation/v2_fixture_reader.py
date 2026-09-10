from copy import deepcopy

from processor.v2_contract import validate_v2_evidence_contract


def _agent_event(
    sequence: int,
    event_type: str,
    action: str,
    status: str,
) -> dict:
    return {
        "sequence": sequence,
        "event_type": event_type,
        "actor": "AGENT",
        "action": action,
        "status": status,
    }


def _tool_execution(
    incident_id: str,
    execution_id: str,
    status: str = "SUCCESS",
) -> dict:
    return {
        "execution_id": execution_id,
        "tool_name": "UPDATE_ACCOUNT",
        "status": status.upper(),
        "request": {
            "account_id": f"ACC-{incident_id[-3:]}",
            "action": "UPDATE_ACCOUNT",
        },
        "response": {
            "status": status.lower(),
            "error_details": (
                "Tool execution failed"
                if status.upper() == "FAILED"
                else None
            ),
        },
        "duration_ms": 1000,
    }


def _evidence(
    incident_id: str,
    correlation_id: str,
    agent_events: list[dict],
    tool_executions: list[dict],
    authoritative_state: str | None,
    state_available: bool,
    telemetry_events: list[dict],
) -> dict:
    return {
        "incident_id": incident_id,
        "correlation_id": correlation_id,
        "agent_execution": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "events": agent_events,
            "provenance": {
                "database": "BigQuery",
                "dataset": "patchamomma",
                "table": "agent_execution_events",
            },
        },
        "tool_execution": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "executions": tool_executions,
            "provenance": {
                "database": "AlloyDB",
                "cluster": "patchamomma-alloydb",
                "instance": "primary",
                "database_name": "postgres",
                "table": "tool_execution",
            },
        },
        "authoritative_state": {
            "incident_id": incident_id,
            "state": (
                {
                    "authoritative_status": authoritative_state,
                }
                if state_available
                else None
            ),
            "state_available": state_available,
            "provenance": {
                "database": "Spanner",
                "instance": "patchamomma-v2",
                "database_name": "patchamomma",
                "table": "account_state",
            },
        },
        "runtime_telemetry": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "events": telemetry_events,
            "provenance": {
                "database": "Bigtable",
                "instance": "patchamomma-v2",
                "table": "runtime_telemetry",
                "column_family": "telemetry",
            },
        },
    }


def _build_fixtures() -> dict[str, dict]:
    fixtures = {}

    # ------------------------------------------------------------------
    # INC-001
    # Tool SUCCESS + authoritative state UNCHANGED
    # Expected conflict:
    # TOOL_SUCCESS_VS_STATE_UNCHANGED
    # ------------------------------------------------------------------
    fixtures["INC-001"] = _evidence(
        incident_id="INC-001",
        correlation_id="CORR-001",
        agent_events=[
            _agent_event(
                1,
                "USER_REQUEST",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
            _agent_event(
                2,
                "AGENT",
                "RETRIEVE_DOCUMENT",
                "SUCCESS",
            ),
            _agent_event(
                3,
                "AGENT",
                "PROCESS_DOCUMENT",
                "WARNING",
            ),
            _agent_event(
                4,
                "AGENT",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
        ],
        tool_executions=[
            _tool_execution(
                "INC-001",
                "EXEC-001",
                "SUCCESS",
            )
        ],
        authoritative_state="UNCHANGED",
        state_available=True,
        telemetry_events=[
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": "EXEC-001",
                "retry_count": "0",
            }
        ],
    )

    # ------------------------------------------------------------------
    # INC-002
    # Clean successful execution
    # ------------------------------------------------------------------
    fixtures["INC-002"] = _evidence(
        incident_id="INC-002",
        correlation_id="CORR-002",
        agent_events=[
            _agent_event(
                1,
                "USER_REQUEST",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
            _agent_event(
                2,
                "AGENT",
                "RETRIEVE_DOCUMENT",
                "SUCCESS",
            ),
            _agent_event(
                3,
                "AGENT",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
        ],
        tool_executions=[
            _tool_execution(
                "INC-002",
                "EXEC-002",
                "SUCCESS",
            )
        ],
        authoritative_state="UPDATED",
        state_available=True,
        telemetry_events=[
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": "EXEC-002",
                "retry_count": "0",
            }
        ],
    )

    # ------------------------------------------------------------------
    # INC-003
    # Successful execution, authoritative state UPDATED
    # ------------------------------------------------------------------
    fixtures["INC-003"] = _evidence(
        incident_id="INC-003",
        correlation_id="CORR-003",
        agent_events=[
            _agent_event(
                1,
                "USER_REQUEST",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
            _agent_event(
                2,
                "AGENT",
                "RETRIEVE_DOCUMENT",
                "SUCCESS",
            ),
            _agent_event(
                3,
                "AGENT",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
        ],
        tool_executions=[
            _tool_execution(
                "INC-003",
                "EXEC-003",
                "SUCCESS",
            )
        ],
        authoritative_state="UPDATED",
        state_available=True,
        telemetry_events=[
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": "EXEC-003",
                "retry_count": "0",
            }
        ],
    )

    # ------------------------------------------------------------------
    # INC-004
    # Tool FAILED + authoritative state UPDATED
    # Expected conflict:
    # TOOL_FAILURE_VS_STATE_UPDATED
    # ------------------------------------------------------------------
    fixtures["INC-004"] = _evidence(
        incident_id="INC-004",
        correlation_id="CORR-004",
        agent_events=[
            _agent_event(
                1,
                "USER_REQUEST",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
            _agent_event(
                2,
                "AGENT",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
        ],
        tool_executions=[
            _tool_execution(
                "INC-004",
                "EXEC-004",
                "FAILED",
            )
        ],
        authoritative_state="UPDATED",
        state_available=True,
        telemetry_events=[
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": "EXEC-004",
                "retry_count": "0",
            }
        ],
    )

    # ------------------------------------------------------------------
    # INC-005
    # Successful execution, authoritative state UPDATED
    # ------------------------------------------------------------------
    fixtures["INC-005"] = _evidence(
        incident_id="INC-005",
        correlation_id="CORR-005",
        agent_events=[
            _agent_event(
                1,
                "USER_REQUEST",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
            _agent_event(
                2,
                "AGENT",
                "RETRIEVE_DOCUMENT",
                "SUCCESS",
            ),
            _agent_event(
                3,
                "AGENT",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
        ],
        tool_executions=[
            _tool_execution(
                "INC-005",
                "EXEC-005",
                "SUCCESS",
            )
        ],
        authoritative_state="UPDATED",
        state_available=True,
        telemetry_events=[
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": "EXEC-005",
                "retry_count": "0",
            }
        ],
    )

    # ------------------------------------------------------------------
    # INC-006
    # Multiple tool executions / repeated invocation
    # Expected:
    # EXEC-006 and EXEC-007 both present
    # ------------------------------------------------------------------
    fixtures["INC-006"] = _evidence(
        incident_id="INC-006",
        correlation_id="CORR-006",
        agent_events=[
            _agent_event(
                1,
                "USER_REQUEST",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
            _agent_event(
                2,
                "AGENT",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
            _agent_event(
                4,
                "AGENT",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
        ],
        tool_executions=[
            _tool_execution(
                "INC-006",
                "EXEC-006",
                "SUCCESS",
            ),
            _tool_execution(
                "INC-006",
                "EXEC-007",
                "SUCCESS",
            ),
        ],
        authoritative_state="UPDATED",
        state_available=True,
        telemetry_events=[
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": "EXEC-006",
                "retry_count": "0",
            },
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": "EXEC-007",
                "retry_count": "0",
            },
        ],
    )

    # ------------------------------------------------------------------
    # INC-007
    # Incomplete evidence:
    # - no tool execution
    # - authoritative state unavailable
    # - telemetry exists
    # Expected outcome:
    # UNCONFIRMED
    # ------------------------------------------------------------------
    fixtures["INC-007"] = _evidence(
        incident_id="INC-007",
        correlation_id="CORR-007",
        agent_events=[
            _agent_event(
                1,
                "USER_REQUEST",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
            _agent_event(
                2,
                "AGENT",
                "RETRIEVE_DOCUMENT",
                "SUCCESS",
            ),
            _agent_event(
                3,
                "AGENT",
                "UPDATE_ACCOUNT",
                "REQUESTED",
            ),
        ],
        tool_executions=[],
        authoritative_state=None,
        state_available=False,
        telemetry_events=[
            {
                "event_type": "TOOL_CALL_COMPLETED",
                "execution_id": None,
                "retry_count": "0",
            }
        ],
    )

    return fixtures


FIXTURES = _build_fixtures()


class V2FixtureReader:
    """
    Evaluation-only V2 evidence reader.

    This reader mirrors the four-source V2 evidence contract without
    connecting to live BigQuery, Spanner, AlloyDB, or Bigtable.

    It is used for deterministic local evaluation and matched
    V1-vs-V2 scenario testing when AlloyDB PSC is not reachable
    from the local development machine.
    """

    def inspect_incident(self, incident_id: str) -> dict:
        if incident_id not in FIXTURES:
            raise KeyError(
                f"No V2 fixture exists for incident {incident_id}"
            )

        evidence = deepcopy(FIXTURES[incident_id])

        # Keep the fixture itself honest: every fixture must satisfy
        # the same V2 contract used by the production reader.
        validate_v2_evidence_contract(evidence)

        return evidence