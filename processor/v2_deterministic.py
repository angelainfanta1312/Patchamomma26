import logging

logger = logging.getLogger(__name__)


def _get_tool_executions(evidence: dict) -> list:
    tool_execution = evidence.get("tool_execution") or {}
    return tool_execution.get("executions") or []


def _get_telemetry_events(evidence: dict) -> list:
    runtime_telemetry = evidence.get("runtime_telemetry") or {}
    return runtime_telemetry.get("events") or []


def _get_authoritative_state(evidence: dict):
    authoritative_state = evidence.get("authoritative_state") or {}

    if not authoritative_state.get("state_available"):
        return None

    return authoritative_state.get("state")


def analyze_v2_evidence(evidence: dict) -> dict:
    """
    Deterministically analyze the four-source V2 evidence package.

    This function does not infer root cause and does not use Gemini.
    It only identifies:
      - confirmed facts supported directly by evidence
      - conflicts between evidence sources
      - missing evidence
      - outcome confirmation status
    """

    incident_id = evidence["incident_id"]
    correlation_id = evidence["correlation_id"]

    agent_execution = evidence.get("agent_execution") or {}
    agent_events = agent_execution.get("events") or []

    tool_executions = _get_tool_executions(evidence)
    telemetry_events = _get_telemetry_events(evidence)
    authoritative_state = _get_authoritative_state(evidence)

    confirmed_facts = []
    conflicts = []
    missing_evidence = []

    # ---------------------------------------------------------
    # 1. Agent execution evidence
    # ---------------------------------------------------------

    if agent_events:
        confirmed_facts.append(
            f"BigQuery contains {len(agent_events)} agent execution "
            f"events for {incident_id}."
        )

    # ---------------------------------------------------------
    # 2. Tool execution evidence
    # ---------------------------------------------------------

    if tool_executions:
        confirmed_facts.append(
            f"AlloyDB contains {len(tool_executions)} tool execution "
            f"record(s) for {incident_id}."
        )

        tool_statuses = [
            execution.get("status")
            for execution in tool_executions
            if execution.get("status") is not None
        ]

        if "SUCCESS" in tool_statuses:
            confirmed_facts.append(
                "At least one tool execution returned SUCCESS."
            )

        if "FAILED" in tool_statuses or "FAILURE" in tool_statuses:
            confirmed_facts.append(
                "At least one tool execution reported a failure."
            )
    else:
        missing_evidence.append(
            {
                "missing_evidence_source": "AlloyDB",
                "reason": "No tool execution records were available.",
            }
        )

    # ---------------------------------------------------------
    # 3. Authoritative state
    # ---------------------------------------------------------

    if authoritative_state is None:
        missing_evidence.append(
            {
                "missing_evidence_source": "Spanner",
                "reason": "Authoritative business state was unavailable.",
            }
        )
    else:
        authoritative_status = authoritative_state.get(
            "authoritative_status"
        )

        if authoritative_status:
            confirmed_facts.append(
                f"Spanner authoritative state is "
                f"{authoritative_status}."
            )

    # ---------------------------------------------------------
    # 4. Runtime telemetry
    # ---------------------------------------------------------

    if telemetry_events:
        confirmed_facts.append(
            f"Bigtable contains {len(telemetry_events)} runtime "
            f"telemetry event(s) for {incident_id}."
        )
    else:
        missing_evidence.append(
            {
                "missing_evidence_source": "Bigtable",
                "reason": "No runtime telemetry records were available.",
            }
        )

    # ---------------------------------------------------------
    # 5. Tool SUCCESS vs authoritative UNCHANGED
    # ---------------------------------------------------------

    tool_statuses = [
        execution.get("status")
        for execution in tool_executions
    ]

    if (
        "SUCCESS" in tool_statuses
        and authoritative_state is not None
        and authoritative_state.get("authoritative_status")
        == "UNCHANGED"
    ):
        conflicts.append(
            {
                "type": "TOOL_SUCCESS_VS_STATE_UNCHANGED",
                "description": (
                    "AlloyDB reports a successful tool execution, "
                    "while Spanner reports that authoritative "
                    "business state remained unchanged."
                ),
            }
        )

    # ---------------------------------------------------------
    # 6. Tool FAILURE vs authoritative UPDATED
    # ---------------------------------------------------------

    has_tool_failure = any(
        status in {"FAILED", "FAILURE"}
        for status in tool_statuses
    )

    if (
        has_tool_failure
        and authoritative_state is not None
        and authoritative_state.get("authoritative_status")
        == "UPDATED"
    ):
        conflicts.append(
            {
                "type": "TOOL_FAILURE_VS_STATE_UPDATED",
                "description": (
                    "AlloyDB reports a failed tool execution, "
                    "while Spanner reports that authoritative "
                    "business state was updated."
                ),
            }
        )

    # ---------------------------------------------------------
    # 7. Determine whether business outcome is confirmable
    # ---------------------------------------------------------

    if authoritative_state is None:
        outcome_confirmation = "UNCONFIRMED"
    else:
        outcome_confirmation = authoritative_state.get(
            "authoritative_status",
            "UNCONFIRMED",
        )

    # ---------------------------------------------------------
    # 8. Replay / repeated execution detection
    # ---------------------------------------------------------

    if len(tool_executions) > 1:
        execution_ids = [
            execution.get("execution_id")
            for execution in tool_executions
            if execution.get("execution_id")
        ]

        if len(execution_ids) > 1:
            confirmed_facts.append(
                f"Multiple tool executions were recorded: "
                f"{', '.join(execution_ids)}."
            )

    # ---------------------------------------------------------
    # 9. Correlation consistency
    # ---------------------------------------------------------

    source_correlation_ids = {
        agent_execution.get("correlation_id"),
        evidence.get("tool_execution", {}).get("correlation_id"),
        evidence.get("authoritative_state", {}).get("correlation_id"),
        evidence.get("runtime_telemetry", {}).get("correlation_id"),
    }

    source_correlation_ids.discard(None)

    if source_correlation_ids and (
        source_correlation_ids != {correlation_id}
    ):
        conflicts.append(
            {
                "type": "CORRELATION_ID_MISMATCH",
                "description": (
                    "Evidence sources contain inconsistent "
                    "correlation IDs."
                ),
            }
        )

    # ---------------------------------------------------------
    # 10. Final deterministic result
    # ---------------------------------------------------------

    result = {
        "incident_id": incident_id,
        "correlation_id": correlation_id,
        "confirmed_facts": confirmed_facts,
        "conflicts": conflicts,
        "missing_evidence": missing_evidence,
        "outcome_confirmation": outcome_confirmation,
        "evidence_counts": {
            "agent_execution_events": len(agent_events),
            "tool_executions": len(tool_executions),
            "runtime_telemetry_events": len(telemetry_events),
        },
    }

    logger.info(
        "V2 deterministic analysis completed for %s: "
        "%d facts, %d conflicts, %d missing evidence items",
        incident_id,
        len(confirmed_facts),
        len(conflicts),
        len(missing_evidence),
    )

    return result