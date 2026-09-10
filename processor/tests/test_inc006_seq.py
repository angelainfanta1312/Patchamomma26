from processor.v2_evidence import V2EvidenceReader


def main():
    reader = V2EvidenceReader()

    evidence = reader.inspect_incident("INC-006")

    events = evidence["agent_execution"]["events"]

    actual = [
        (event["sequence_number"], event["event_type"])
        for event in events
    ]

    expected = [
        (1, "USER_REQUEST"),
        (2, "TOOL_CALL"),
        (4, "TOOL_CALL"),
    ]

    print("\n=== INC-006 SEQUENCE TEST ===")
    print("Actual:  ", actual)
    print("Expected:", expected)

    if actual == expected:
        print("PASS")
    else:
        print("FAIL")


if __name__ == "__main__":
    main()