from processor.v2_evidence import V2EvidenceReader


class FakeBigQueryReader:
    def inspect_agent_execution(self, incident_id: str) -> dict:
        return {
            "incident_id": incident_id,
            "correlation_id": "CORR-006",
            "events": [
                {
                    "sequence_number": 1,
                    "timestamp": "2026-08-18T11:30:00+00:00",
                    "source": "USER",
                    "event_type": "USER_REQUEST",
                    "actor": "user",
                    "action": "UPDATE_ACCOUNT",
                    "status": "REQUESTED",
                    "details": "User requested account update.",
                },
                {
                    "sequence_number": 2,
                    "timestamp": "2026-08-18T11:30:02+00:00",
                    "source": "AGENT",
                    "event_type": "TOOL_CALL",
                    "actor": "agent",
                    "action": "UPDATE_ACCOUNT",
                    "status": "REQUESTED",
                    "details": "Agent issued first update call.",
                },
                {
                    "sequence_number": 4,
                    "timestamp": "2026-08-18T11:30:05+00:00",
                    "source": "AGENT",
                    "event_type": "TOOL_CALL",
                    "actor": "agent",
                    "action": "UPDATE_ACCOUNT",
                    "status": "REQUESTED",
                    "details": "Agent issued repeated update call.",
                },
            ],
            "provenance": {
                "database": "BigQuery",
                "dataset": "patchamomma",
                "view": "agent_execution_events",
            },
        }


class FakeSpannerReader:
    def inspect_authoritative_state(self, incident_id: str) -> dict:
        return {
            "incident_id": incident_id,
            "correlation_id": "CORR-006",
            "state": {
                "account_id": "ACC-006",
                "requested_action": "UPDATE_ACCOUNT",
                "authoritative_status": "UPDATED",
                "state_version": 52,
                "last_modified_at": "2026-08-18T11:30:06+00:00",
                "last_modified_by": "account-service",
                "state_available": True,
                "state_details": (
                    "Authoritative account state reflects "
                    "the requested account update after "
                    "repeated tool calls."
                ),
            },
            "state_available": True,
            "provenance": {
                "database": "Spanner",
                "instance": "patchamomma-v2",
                "database_name": "patchamomma",
                "table": "account_state",
            },
        }


class FakeAlloyDBReader:
    def inspect_tool_execution(self, incident_id: str) -> dict:
        return {
            "incident_id": incident_id,
            "correlation_id": "CORR-006",
            "executions": [
                {
                    "execution_id": "EXEC-006",
                    "tool_name": "UPDATE_ACCOUNT",
                    "status": "SUCCESS",
                    "started_at": "2026-08-18T11:30:03+00:00",
                    "completed_at": "2026-08-18T11:30:04+00:00",
                    "duration_ms": 1000,
                    "request": "UPDATE_ACCOUNT ACC-006",
                    "response": "Account updated.",
                    "error_details": None,
                },
                {
                    "execution_id": "EXEC-007",
                    "tool_name": "UPDATE_ACCOUNT",
                    "status": "SUCCESS",
                    "started_at": "2026-08-18T11:30:05+00:00",
                    "completed_at": "2026-08-18T11:30:06+00:00",
                    "duration_ms": 1000,
                    "request": "UPDATE_ACCOUNT ACC-006",
                    "response": "Account already updated.",
                    "error_details": None,
                },
            ],
            "provenance": {
                "database": "AlloyDB",
                "database_name": "patchamomma",
                "table": "tool_execution",
            },
        }


class FakeBigtableReader:
    def inspect_runtime_telemetry(self, incident_id: str) -> dict:
        return {
            "incident_id": incident_id,
            "correlation_id": "CORR-006",
            "events": [
                {
                    "timestamp": "2026-08-18T11:30:03+00:00",
                    "event_type": "TOOL_EXECUTION",
                    "status": "SUCCESS",
                    "execution_id": "EXEC-006",
                    "run_id": "RUN-006",
                    "latency_ms": 1000,
                    "retry_count": 0,
                    "details": "First tool execution completed.",
                },
                {
                    "timestamp": "2026-08-18T11:30:05+00:00",
                    "event_type": "TOOL_EXECUTION",
                    "status": "SUCCESS",
                    "execution_id": "EXEC-007",
                    "run_id": "RUN-006",
                    "latency_ms": 1000,
                    "retry_count": 1,
                    "details": "Repeated tool execution completed.",
                },
            ],
            "provenance": {
                "database": "Bigtable",
                "table": "runtime_telemetry",
            },
        }


def main():
    reader = V2EvidenceReader(
        bigquery_reader=FakeBigQueryReader(),
        spanner_reader=FakeSpannerReader(),
        alloydb_reader=FakeAlloyDBReader(),
        bigtable_reader=FakeBigtableReader(),
    )

    evidence = reader.inspect_incident("INC-006")

    print("\n=== V2 AGGREGATION TEST ===")

    print("Incident ID:", evidence["incident_id"])
    print("Correlation ID:", evidence["correlation_id"])

    print(
        "BigQuery agent events:",
        len(evidence["agent_execution"]["events"]),
    )

    print(
        "AlloyDB executions:",
        len(evidence["tool_execution"]["executions"]),
    )

    print(
        "Bigtable telemetry events:",
        len(evidence["runtime_telemetry"]["events"]),
    )

    print(
        "Spanner authoritative status:",
        evidence["authoritative_state"]["state"][
            "authoritative_status"
        ],
    )

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------

    assert evidence["incident_id"] == "INC-006"
    assert evidence["correlation_id"] == "CORR-006"

    # BigQuery preserves the agent sequence gaps.
    agent_sequence = [
        event["sequence_number"]
        for event in evidence["agent_execution"]["events"]
    ]

    assert agent_sequence == [1, 2, 4]

    # AlloyDB preserves BOTH executions.
    executions = evidence["tool_execution"]["executions"]

    assert len(executions) == 2
    assert executions[0]["execution_id"] == "EXEC-006"
    assert executions[1]["execution_id"] == "EXEC-007"

    # Bigtable preserves telemetry for both executions.
    telemetry = evidence["runtime_telemetry"]["events"]

    assert len(telemetry) == 2
    assert telemetry[0]["execution_id"] == "EXEC-006"
    assert telemetry[1]["execution_id"] == "EXEC-007"

    # Spanner remains authoritative.
    assert (
        evidence["authoritative_state"]["state"][
            "authoritative_status"
        ]
        == "UPDATED"
    )

    # Provenance must identify each database correctly.
    assert (
        evidence["agent_execution"]["provenance"]["database"]
        == "BigQuery"
    )

    assert (
        evidence["tool_execution"]["provenance"]["database"]
        == "AlloyDB"
    )

    assert (
        evidence["authoritative_state"]["provenance"]["database"]
        == "Spanner"
    )

    assert (
        evidence["runtime_telemetry"]["provenance"]["database"]
        == "Bigtable"
    )

    print("\nPASS — four-source evidence aggregation works.")
    print("PASS — INC-006 replay evidence preserved.")
    print("PASS — source provenance preserved.")
    print("PASS — authoritative state remains separate from tool/telemetry evidence.")
    print("\n===============================")


if __name__ == "__main__":
    main()