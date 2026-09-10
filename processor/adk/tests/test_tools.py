from processor.adk.tools import (
    get_agent_execution,
    get_authoritative_state,
    get_runtime_telemetry,
)


def main():
    print("\n=== PATCHAMOMMA ADK TOOL TEST ===\n")

    incident_id = "INC-001"

    agent = get_agent_execution(incident_id)
    print(
        f"BigQuery: {len(agent['events'])} agent events"
    )

    state = get_authoritative_state(incident_id)
    print(
        "Spanner:",
        state["state"]["authoritative_status"]
        if state["state"]
        else None,
    )

    telemetry = get_runtime_telemetry(incident_id)
    print(
        f"Bigtable: {len(telemetry['events'])} telemetry events"
    )

    print("\nALL REAL ADK TOOL FUNCTIONS PASSED\n")


if __name__ == "__main__":
    main()