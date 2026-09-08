from processor.v2_deterministic import analyze_v2_evidence


def make_evidence(
    incident_id,
    correlation_id,
    tool_statuses,
    authoritative_status,
    state_available=True,
    telemetry_count=1,
):
    tool_executions = [
        {
            "execution_id": f"EXEC-{index}",
            "status": status,
        }
        for index, status in enumerate(tool_statuses, start=1)
    ]

    telemetry_events = [
        {
            "execution_id": f"EXEC-{index}",
            "status": "SUCCESS",
        }
        for index in range(1, telemetry_count + 1)
    ]

    state = None

    if state_available:
        state = {
            "account_id": f"ACC-{incident_id[-3:]}",
            "requested_action": "UPDATE_ACCOUNT",
            "authoritative_status": authoritative_status,
            "state_available": True,
        }

    return {
        "incident_id": incident_id,
        "correlation_id": correlation_id,
        "agent_execution": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "events": [
                {
                    "sequence_number": 1,
                    "event_type": "USER_REQUEST",
                },
                {
                    "sequence_number": 2,
                    "event_type": "TOOL_CALL",
                },
            ],
            "provenance": {
                "database": "BigQuery",
            },
        },
        "tool_execution": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "executions": tool_executions,
            "provenance": {
                "database": "AlloyDB",
            },
        },
        "authoritative_state": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "state": state,
            "state_available": state_available,
            "provenance": {
                "database": "Spanner",
            },
        },
        "runtime_telemetry": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "events": telemetry_events,
            "provenance": {
                "database": "Bigtable",
            },
        },
    }


def assert_conflict(result, conflict_type):
    conflict_types = {
        conflict["type"]
        for conflict in result["conflicts"]
    }

    assert conflict_type in conflict_types


def assert_missing_source(result, source):
    sources = {
        item["missing_evidence_source"]
        for item in result["missing_evidence"]
    }

    assert source in sources


def test_inc001():
    evidence = make_evidence(
        "INC-001",
        "CORR-001",
        ["SUCCESS"],
        "UNCHANGED",
    )

    result = analyze_v2_evidence(evidence)

    assert result["outcome_confirmation"] == "UNCHANGED"

    assert_conflict(
        result,
        "TOOL_SUCCESS_VS_STATE_UNCHANGED",
    )


def test_inc002():
    evidence = make_evidence(
        "INC-002",
        "CORR-002",
        ["SUCCESS"],
        "UPDATED",
    )

    result = analyze_v2_evidence(evidence)

    assert result["outcome_confirmation"] == "UPDATED"

    assert result["conflicts"] == []
    assert result["missing_evidence"] == []


def test_inc003():
    evidence = make_evidence(
        "INC-003",
        "CORR-003",
        ["SUCCESS"],
        "UPDATED",
    )

    result = analyze_v2_evidence(evidence)

    assert result["outcome_confirmation"] == "UPDATED"

    # The deterministic layer cannot infer the missing AUDIT
    # source because AUDIT is not part of the four-source V2
    # evidence package yet.
    assert result["conflicts"] == []


def test_inc004():
    evidence = make_evidence(
        "INC-004",
        "CORR-004",
        ["FAILED"],
        "UPDATED",
    )

    result = analyze_v2_evidence(evidence)

    assert result["outcome_confirmation"] == "UPDATED"

    assert_conflict(
        result,
        "TOOL_FAILURE_VS_STATE_UPDATED",
    )


def test_inc005():
    evidence = make_evidence(
        "INC-005",
        "CORR-005",
        ["SUCCESS"],
        "UPDATED",
    )

    result = analyze_v2_evidence(evidence)

    assert result["outcome_confirmation"] == "UPDATED"

    assert result["conflicts"] == []


def test_inc006():
    evidence = make_evidence(
        "INC-006",
        "CORR-006",
        ["SUCCESS", "SUCCESS"],
        "UPDATED",
        telemetry_count=2,
    )

    result = analyze_v2_evidence(evidence)

    assert result["outcome_confirmation"] == "UPDATED"

    assert result["evidence_counts"]["tool_executions"] == 2
    assert result["evidence_counts"]["runtime_telemetry_events"] == 2

    fact_text = " ".join(result["confirmed_facts"])

    assert "EXEC-1" in fact_text
    assert "EXEC-2" in fact_text


def test_inc007():
    evidence = make_evidence(
        "INC-007",
        "CORR-007",
        [],
        None,
        state_available=False,
        telemetry_count=1,
    )

    result = analyze_v2_evidence(evidence)

    assert result["outcome_confirmation"] == "UNCONFIRMED"

    assert_missing_source(result, "AlloyDB")
    assert_missing_source(result, "Spanner")


def main():
    tests = [
        ("INC-001", test_inc001),
        ("INC-002", test_inc002),
        ("INC-003", test_inc003),
        ("INC-004", test_inc004),
        ("INC-005", test_inc005),
        ("INC-006", test_inc006),
        ("INC-007", test_inc007),
    ]

    print("\n=== V2 DETERMINISTIC TEST ===")

    for incident_id, test in tests:
        test()
        print(f"{incident_id}: PASS")

    print("\n==============================")
    print("ALL 7 DETERMINISTIC TESTS PASSED")


if __name__ == "__main__":
    main()