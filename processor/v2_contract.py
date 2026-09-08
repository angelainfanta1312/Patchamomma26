from typing import Any


def validate_v2_evidence_contract(evidence: dict) -> None:
    required_top_level = {
        "incident_id",
        "correlation_id",
        "agent_execution",
        "tool_execution",
        "authoritative_state",
        "runtime_telemetry",
    }

    missing = required_top_level - evidence.keys()
    if missing:
        raise ValueError(
            f"Missing V2 evidence fields: {sorted(missing)}"
        )

    if not evidence["incident_id"]:
        raise ValueError("incident_id cannot be empty")

    if not evidence["correlation_id"]:
        raise ValueError("correlation_id cannot be empty")

    # ---------------------------------------------------------
    # 1. BigQuery — Agent execution
    # ---------------------------------------------------------
    agent = evidence["agent_execution"]

    required_agent_fields = {
        "incident_id",
        "correlation_id",
        "events",
        "provenance",
    }

    missing_agent = required_agent_fields - agent.keys()
    if missing_agent:
        raise ValueError(
            f"Missing agent execution fields: "
            f"{sorted(missing_agent)}"
        )

    if not isinstance(agent["events"], list):
        raise ValueError(
            "agent_execution.events must be a list"
        )

    if agent["provenance"].get("database") != "BigQuery":
        raise ValueError(
            "Agent execution provenance must identify BigQuery"
        )

    # ---------------------------------------------------------
    # 2. AlloyDB — Tool execution
    # ---------------------------------------------------------
    tool = evidence["tool_execution"]

    required_tool_fields = {
        "incident_id",
        "correlation_id",
        "executions",
        "provenance",
    }

    missing_tool = required_tool_fields - tool.keys()
    if missing_tool:
        raise ValueError(
            f"Missing tool execution fields: "
            f"{sorted(missing_tool)}"
        )

    if not isinstance(tool["executions"], list):
        raise ValueError(
            "tool_execution.executions must be a list"
        )

    if tool["provenance"].get("database") != "AlloyDB":
        raise ValueError(
            "Tool execution provenance must identify AlloyDB"
        )

    # ---------------------------------------------------------
    # 3. Spanner — Authoritative business state
    # ---------------------------------------------------------
    authoritative = evidence["authoritative_state"]

    required_state_fields = {
        "incident_id",
        "state",
        "state_available",
        "provenance",
    }

    missing_state = required_state_fields - authoritative.keys()
    if missing_state:
        raise ValueError(
            f"Missing authoritative state fields: "
            f"{sorted(missing_state)}"
        )

    if authoritative["provenance"].get("database") != "Spanner":
        raise ValueError(
            "Authoritative state provenance must identify Spanner"
        )

    if authoritative["state_available"]:
        if authoritative["state"] is None:
            raise ValueError(
                "state_available=True but state is missing"
            )
    else:
        if authoritative["state"] is not None:
            raise ValueError(
                "state_available=False but state exists"
            )

    # ---------------------------------------------------------
    # 4. Bigtable — Runtime telemetry
    # ---------------------------------------------------------
    telemetry = evidence["runtime_telemetry"]

    required_telemetry_fields = {
        "incident_id",
        "correlation_id",
        "events",
        "provenance",
    }

    missing_telemetry = (
        required_telemetry_fields - telemetry.keys()
    )

    if missing_telemetry:
        raise ValueError(
            f"Missing runtime telemetry fields: "
            f"{sorted(missing_telemetry)}"
        )

    if not isinstance(telemetry["events"], list):
        raise ValueError(
            "runtime_telemetry.events must be a list"
        )

    if telemetry["provenance"].get("database") != "Bigtable":
        raise ValueError(
            "Runtime telemetry provenance must identify Bigtable"
        )