from processor.v2_gemini_input import (
    build_gemini_input,
    build_gemini_prompt,
)


def make_evidence(
    incident_id,
    correlation_id,
    tool_status,
    authoritative_status,
):
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
                    "action": "UPDATE_ACCOUNT",
                },
                {
                    "sequence_number": 2,
                    "event_type": "TOOL_CALL",
                    "action": "UPDATE_ACCOUNT",
                },
            ],
            "provenance": {
                "database": "BigQuery",
            },
        },

        "tool_execution": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "executions": [
                {
                    "execution_id": f"EXEC-{incident_id[-3:]}",
                    "tool_name": "UPDATE_ACCOUNT",
                    "status": tool_status,
                }
            ],
            "provenance": {
                "database": "AlloyDB",
            },
        },

        "authoritative_state": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "state": (
                {
                    "account_id": f"ACC-{incident_id[-3:]}",
                    "requested_action": "UPDATE_ACCOUNT",
                    "authoritative_status": authoritative_status,
                }
                if authoritative_status is not None
                else None
            ),
            "state_available": authoritative_status is not None,
            "provenance": {
                "database": "Spanner",
            },
        },

        "runtime_telemetry": {
            "incident_id": incident_id,
            "correlation_id": correlation_id,
            "events": [
                {
                    "event_type": "TOOL_EXECUTION",
                    "status": tool_status,
                    "execution_id": f"EXEC-{incident_id[-3:]}",
                }
            ],
            "provenance": {
                "database": "Bigtable",
            },
        },
    }


def test_inc001():
    evidence = make_evidence(
        "INC-001",
        "CORR-001",
        "SUCCESS",
        "UNCHANGED",
    )

    gemini_input = build_gemini_input(evidence)

    assert gemini_input["incident_id"] == "INC-001"
    assert gemini_input["correlation_id"] == "CORR-001"

    # All four evidence sources must survive.
    assert "agent_execution" in gemini_input["evidence"]
    assert "tool_execution" in gemini_input["evidence"]
    assert "authoritative_state" in gemini_input["evidence"]
    assert "runtime_telemetry" in gemini_input["evidence"]

    # Deterministic conflict must survive into Gemini input.
    conflicts = gemini_input["deterministic_findings"]["conflicts"]

    conflict_types = {
        conflict["type"]
        for conflict in conflicts
    }

    assert "TOOL_SUCCESS_VS_STATE_UNCHANGED" in conflict_types


def test_inc004():
    evidence = make_evidence(
        "INC-004",
        "CORR-004",
        "FAILED",
        "UPDATED",
    )

    gemini_input = build_gemini_input(evidence)

    conflicts = gemini_input["deterministic_findings"]["conflicts"]

    conflict_types = {
        conflict["type"]
        for conflict in conflicts
    }

    assert "TOOL_FAILURE_VS_STATE_UPDATED" in conflict_types


def test_prompt_contains_evidence_rules():
    evidence = make_evidence(
        "INC-001",
        "CORR-001",
        "SUCCESS",
        "UNCHANGED",
    )

    prompt = build_gemini_prompt(evidence)

    assert "BigQuery" in prompt
    assert "AlloyDB" in prompt
    assert "Spanner" in prompt
    assert "Bigtable" in prompt

    assert (
        "tool SUCCESS as proof that business state changed"
        in prompt
    )

    assert (
        "tool FAILURE as proof that business state remained unchanged"
        in prompt
    )

    assert "invent evidence" in prompt.lower()
    assert "root causes" in prompt.lower()


def main():
    print("\n=== V2 GEMINI INPUT TEST ===")

    test_inc001()
    print("INC-001 conflict preservation: PASS")

    test_inc004()
    print("INC-004 conflict preservation: PASS")

    test_prompt_contains_evidence_rules()
    print("Gemini evidence rules: PASS")

    print("\n==============================")
    print("ALL V2 GEMINI INPUT TESTS PASSED")


if __name__ == "__main__":
    main()