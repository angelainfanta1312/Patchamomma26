from processor.v2_evidence import V2EvidenceReader


def main():
    reader = V2EvidenceReader()

    test_cases = {
        "INC-001": "UNCHANGED",
        "INC-002": "UPDATED",
        "INC-003": "UPDATED",
        "INC-004": "UPDATED",
        "INC-005": "UPDATED",
        "INC-006": "UPDATED",
        "INC-007": None,
    }

    print("\n=== V2 EVIDENCE TEST ===")

    all_passed = True

    for incident_id, expected_status in test_cases.items():
        print(f"\n--- {incident_id} ---")

        evidence = reader.inspect_incident(incident_id)

        actual_status = None

        authoritative_state = evidence["authoritative_state"]

        if authoritative_state["state_available"]:
            actual_status = authoritative_state["state"][
                "authoritative_status"
            ]

        print("Incident ID:", evidence["incident_id"])
        print("correlation ID:", evidence["corelation_id"])
        print("Agent events:", len(evidence["agent_execution"]["events"]))
        print("Authoritative status:", actual_status)

        if actual_status == expected_status:
            print("PASS")
        else:
            print(
                f"FAIL — expected {expected_status}, "
                f"got {actual_status}"
            )
            all_passed = False

    print("\n==========================")

    if all_passed:
        print("ALL V2 EVIDENCE TESTS PASSED")
    else:
        print("V2 EVIDENCE TESTS FAILED")


if __name__ == "__main__":
    main()