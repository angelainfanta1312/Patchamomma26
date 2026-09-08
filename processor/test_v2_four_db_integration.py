from processor.v2_evidence import V2EvidenceReader
from processor.v2_deterministic import analyze_v2_evidence


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_incident(reader, incident_id, expected):
    print(f"\n--- {incident_id} ---")

    evidence = reader.inspect_incident(incident_id)

    # ---------------------------------------------------------
    # Common identity checks
    # ---------------------------------------------------------

    check(
        evidence["incident_id"] == incident_id,
        f"Wrong incident_id: {evidence['incident_id']}",
    )

    check(
        evidence["correlation_id"] == expected["correlation_id"],
        (
            f"Wrong correlation_id: "
            f"{evidence['correlation_id']} "
            f"(expected {expected['correlation_id']})"
        ),
    )

    # ---------------------------------------------------------
    # Source presence
    # ---------------------------------------------------------

    check(
        evidence["agent_execution"]["provenance"]["database"]
        == "BigQuery",
        "Agent execution provenance is not BigQuery",
    )

    check(
        evidence["tool_execution"]["provenance"]["database"]
        == "AlloyDB",
        "Tool execution provenance is not AlloyDB",
    )

    check(
        evidence["authoritative_state"]["provenance"]["database"]
        == "Spanner",
        "Authoritative state provenance is not Spanner",
    )

    check(
        evidence["runtime_telemetry"]["provenance"]["database"]
        == "Bigtable",
        "Runtime telemetry provenance is not Bigtable",
    )

    # ---------------------------------------------------------
    # BigQuery
    # ---------------------------------------------------------

    agent_events = evidence["agent_execution"]["events"]

    print("BigQuery agent events:", len(agent_events))

    check(
        len(agent_events) == expected["agent_event_count"],
        (
            f"Expected {expected['agent_event_count']} BigQuery "
            f"events, got {len(agent_events)}"
        ),
    )

    if "agent_sequences" in expected:
        actual_sequences = [
            event["sequence_number"]
            for event in agent_events
        ]

        check(
            actual_sequences == expected["agent_sequences"],
            (
                f"BigQuery sequence mismatch: "
                f"{actual_sequences} "
                f"(expected {expected['agent_sequences']})"
            ),
        )

    # ---------------------------------------------------------
    # AlloyDB
    # ---------------------------------------------------------

    executions = evidence["tool_execution"]["executions"]

    print("AlloyDB executions:", len(executions))

    check(
        len(executions) == expected["tool_execution_count"],
        (
            f"Expected {expected['tool_execution_count']} AlloyDB "
            f"executions, got {len(executions)}"
        ),
    )

    actual_execution_ids = [
        execution.get("execution_id")
        for execution in executions
    ]

    if "execution_ids" in expected:
        check(
            actual_execution_ids == expected["execution_ids"],
            (
                f"AlloyDB execution IDs mismatch: "
                f"{actual_execution_ids} "
                f"(expected {expected['execution_ids']})"
            ),
        )

    if "tool_statuses" in expected:
        actual_statuses = [
            execution.get("status")
            for execution in executions
        ]

        check(
            actual_statuses == expected["tool_statuses"],
            (
                f"AlloyDB statuses mismatch: "
                f"{actual_statuses} "
                f"(expected {expected['tool_statuses']})"
            ),
        )

    # ---------------------------------------------------------
    # Spanner
    # ---------------------------------------------------------

    authoritative = evidence["authoritative_state"]

    actual_state_available = authoritative["state_available"]

    print(
        "Spanner state available:",
        actual_state_available,
    )

    check(
        actual_state_available
        == expected["state_available"],
        (
            f"Expected Spanner state_available="
            f"{expected['state_available']}, "
            f"got {actual_state_available}"
        ),
    )

    if expected["state_available"]:
        state = authoritative["state"]

        check(
            state is not None,
            "Spanner says state is available but state is None",
        )

        actual_status = state["authoritative_status"]

        print(
            "Spanner authoritative status:",
            actual_status,
        )

        check(
            actual_status
            == expected["authoritative_status"],
            (
                f"Expected Spanner status "
                f"{expected['authoritative_status']}, "
                f"got {actual_status}"
            ),
        )

    else:
        check(
            authoritative["state"] is None,
            "Spanner state should be None when unavailable",
        )

    # ---------------------------------------------------------
    # Bigtable
    # ---------------------------------------------------------

    telemetry = evidence["runtime_telemetry"]["events"]

    print(
        "Bigtable telemetry events:",
        len(telemetry),
    )

    check(
        len(telemetry) == expected["telemetry_count"],
        (
            f"Expected {expected['telemetry_count']} Bigtable "
            f"telemetry events, got {len(telemetry)}"
        ),
    )

    if "telemetry_execution_ids" in expected:
        actual_telemetry_execution_ids = [
            event.get("execution_id")
            for event in telemetry
        ]

        check(
            actual_telemetry_execution_ids
            == expected["telemetry_execution_ids"],
            (
                f"Bigtable execution IDs mismatch: "
                f"{actual_telemetry_execution_ids} "
                f"(expected "
                f"{expected['telemetry_execution_ids']})"
            ),
        )

    # ---------------------------------------------------------
    # Deterministic analysis
    # ---------------------------------------------------------

    result = analyze_v2_evidence(evidence)

    conflict_types = {
        conflict["type"]
        for conflict in result["conflicts"]
    }

    print(
        "Deterministic conflicts:",
        sorted(conflict_types),
    )

    print(
        "Outcome confirmation:",
        result["outcome_confirmation"],
    )

    for expected_conflict in expected.get(
        "expected_conflicts",
        [],
    ):
        check(
            expected_conflict in conflict_types,
            (
                f"Expected conflict "
                f"{expected_conflict} not found. "
                f"Actual conflicts: {sorted(conflict_types)}"
            ),
        )

    check(
        result["outcome_confirmation"]
        == expected["outcome_confirmation"],
        (
            f"Expected outcome "
            f"{expected['outcome_confirmation']}, "
            f"got {result['outcome_confirmation']}"
        ),
    )

    print("PASS")


def main():
    print("\n=== V2 FOUR-DB INTEGRATION TEST ===")

    reader = V2EvidenceReader()

    test_cases = {
        "INC-001": {
            "correlation_id": "CORR-001",
            "agent_event_count": 4,
            "agent_sequences": [1, 2, 3, 4],
            "tool_execution_count": 1,
            "execution_ids": ["EXEC-001"],
            "tool_statuses": ["SUCCESS"],
            "state_available": True,
            "authoritative_status": "UNCHANGED",
            "telemetry_count": 1,
            "expected_conflicts": [
                "TOOL_SUCCESS_VS_STATE_UNCHANGED",
            ],
            "outcome_confirmation": "UNCHANGED",
        },

        "INC-002": {
            "correlation_id": "CORR-002",
            "agent_event_count": 3,
            "agent_sequences": [1, 2, 3],
            "tool_execution_count": 1,
            "execution_ids": ["EXEC-002"],
            "tool_statuses": ["SUCCESS"],
            "state_available": True,
            "authoritative_status": "UPDATED",
            "telemetry_count": 1,
            "expected_conflicts": [],
            "outcome_confirmation": "UPDATED",
        },

        "INC-003": {
            "correlation_id": "CORR-003",
            "agent_event_count": 3,
            "agent_sequences": [1, 2, 3],
            "tool_execution_count": 1,
            "execution_ids": ["EXEC-003"],
            "tool_statuses": ["SUCCESS"],
            "state_available": True,
            "authoritative_status": "UPDATED",
            "telemetry_count": 1,
            "expected_conflicts": [],
            "outcome_confirmation": "UPDATED",
        },

        "INC-004": {
            "correlation_id": "CORR-004",
            "agent_event_count": 2,
            "agent_sequences": [1, 2],
            "tool_execution_count": 1,
            "execution_ids": ["EXEC-004"],
            "tool_statuses": ["FAILED"],
            "state_available": True,
            "authoritative_status": "UPDATED",
            "telemetry_count": 1,
            "expected_conflicts": [
                "TOOL_FAILURE_VS_STATE_UPDATED",
            ],
            "outcome_confirmation": "UPDATED",
        },

        "INC-005": {
            "correlation_id": "CORR-005",
            "agent_event_count": 3,
            "agent_sequences": [1, 2, 3],
            "tool_execution_count": 1,
            "execution_ids": ["EXEC-005"],
            "tool_statuses": ["SUCCESS"],
            "state_available": True,
            "authoritative_status": "UPDATED",
            "telemetry_count": 1,
            "expected_conflicts": [],
            "outcome_confirmation": "UPDATED",
        },

        "INC-006": {
            "correlation_id": "CORR-006",
            "agent_event_count": 3,
            "agent_sequences": [1, 2, 4],
            "tool_execution_count": 2,
            "execution_ids": [
                "EXEC-006",
                "EXEC-007",
            ],
            "tool_statuses": [
                "SUCCESS",
                "SUCCESS",
            ],
            "state_available": True,
            "authoritative_status": "UPDATED",
            "telemetry_count": 2,
            "telemetry_execution_ids": [
                "EXEC-006",
                "EXEC-007",
            ],
            "expected_conflicts": [],
            "outcome_confirmation": "UPDATED",
        },

        "INC-007": {
            "correlation_id": "CORR-007",
            "agent_event_count": 3,
            "agent_sequences": [1, 2, 3],
            "tool_execution_count": 0,
            "execution_ids": [],
            "tool_statuses": [],
            "state_available": False,
            "authoritative_status": None,
            "telemetry_count": 1,
            "expected_conflicts": [],
            "outcome_confirmation": "UNCONFIRMED",
        },
    }

    passed = 0

    for incident_id, expected in test_cases.items():
        try:
            test_incident(
                reader,
                incident_id,
                expected,
            )
            passed += 1

        except AssertionError as error:
            print(f"FAIL — {error}")

    print("\n==============================")
    print(
        f"RESULT: {passed}/{len(test_cases)} incidents passed"
    )

    if passed == len(test_cases):
        print("ALL FOUR-DB INTEGRATION TESTS PASSED")
    else:
        print("FOUR-DB INTEGRATION TESTS FAILED")


if __name__ == "__main__":
    main()