from typing import Any


def validate_v2_evidence_contract(evidence: dict) -> None:
    """
    Validate the structural contract exchanged between the
    evidence layer and the future ADK investigator.

    Raises ValueError when the contract is invalid.
    """

    required_top_level = {
        "incident_id",
        "corelation_id",
        "agent_execution",
        "authoritative_state",
    }

    missing = required_top_level - evidence.keys()

    if missing:
        raise ValueError(
            f"Missing V2 evidence fields: {sorted(missing)}"
        )

    if not evidence["incident_id"]:
        raise ValueError("incident_id cannot be empty")

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
            "Missing agent execution fields: "
            f"{sorted(missing_agent)}"
        )

    if not isinstance(agent["events"], list):
        raise ValueError("agent_execution.events must be a list")

    provenance = agent["provenance"]

    if provenance.get("database") != "BigQuery":
        raise ValueError(
            "Agent execution provenance must identify BigQuery"
        )

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
            "Missing authoritative state fields: "
            f"{sorted(missing_state)}"
        )

    state_provenance = authoritative["provenance"]

    if state_provenance.get("database") != "Spanner":
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