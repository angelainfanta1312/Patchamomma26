from processor.bigtable_reader import BigtableReader


def main():
    print("\n=== BIGTABLE READER TEST ===\n")

    reader = BigtableReader()

    incidents = [
        "INC-001",
        "INC-002",
        "INC-003",
        "INC-004",
        "INC-005",
        "INC-006",
        "INC-007",
    ]

    expected = {
        "INC-001": 1,
        "INC-002": 1,
        "INC-003": 1,
        "INC-004": 1,
        "INC-005": 1,
        "INC-006": 2,
        "INC-007": 1,
    }

    all_passed = True

    for incident_id in incidents:
        print(f"--- {incident_id} ---")

        try:
            result = reader.inspect_runtime_telemetry(incident_id)

            events = result["events"]

            print(f"Correlation ID: {result['correlation_id']}")
            print(f"Telemetry events: {len(events)}")
            print(f"Provenance: {result['provenance']}")

            for event in events:
                print(
                    f"  {event.get('event_type')} | "
                    f"execution={event.get('execution_id')} | "
                    f"timestamp={event.get('timestamp')} | "
                    f"retry={event.get('retry_count')}"
                )

            expected_count = expected[incident_id]

            if len(events) != expected_count:
                print(
                    f"FAIL — expected {expected_count} "
                    f"event(s), got {len(events)}"
                )
                all_passed = False
                continue

            # Every returned event should belong to this incident.
            if any(
                event.get("incident_id") != incident_id
                for event in events
            ):
                print("FAIL — event from wrong incident returned")
                all_passed = False
                continue

            # INC-006 must preserve both executions.
            if incident_id == "INC-006":
                execution_ids = [
                    event.get("execution_id")
                    for event in events
                ]

                expected_ids = ["EXEC-006", "EXEC-007"]

                if execution_ids != expected_ids:
                    print(
                        "FAIL — INC-006 execution IDs do not match:"
                        f" expected {expected_ids}, got {execution_ids}"
                    )
                    all_passed = False
                    continue

                print("PASS — INC-006 replay executions preserved")

            print("PASS")

        except Exception as exc:
            print(f"FAIL — {type(exc).__name__}: {exc}")
            all_passed = False

        print()

    print("==============================")

    if all_passed:
        print("ALL BIGTABLE READER TESTS PASSED")
    else:
        print("BIGTABLE READER TESTS FAILED")

    print("==============================\n")

    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()