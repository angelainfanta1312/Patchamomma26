import json

from processor.bigquery_reader import BigQueryReader
from processor.incident_processor import IncidentProcessor


def main() -> None:
    reader = BigQueryReader()
    processor = IncidentProcessor()

    incident_ids = [
        "INC-001",
        "INC-002",
        "INC-003",
        "INC-004",
        "INC-005",
        "INC-006",
        "INC-007",
    ]

    required_fields = {
        "incident_id",
        "corelation_id",
        "evidence_count",
        "timeline",
        "missing_evidence",
        "conflicts",
    }

    print("=== WORKSTREAM A CONTRACT VALIDATION ===")

    for incident_id in incident_ids:
        print(f"\nChecking {incident_id}...")

        raw_incident = reader.get_incident(incident_id)
        processed = processor.process(raw_incident)

        # Validate required contract fields.
        assert required_fields.issubset(processed.keys())

        # Validate JSON serialization.
        json.dumps(processed)

        # Validate core collection types.
        assert isinstance(processed["timeline"], list)
        assert isinstance(processed["missing_evidence"], list)
        assert isinstance(processed["conflicts"], list)

        print(
            f"  Evidence: {processed['evidence_count']}"
        )
        print(
            f"  Timeline events: {len(processed['timeline'])}"
        )
        print(
            f"  Missing evidence: {len(processed['missing_evidence'])}"
        )
        print(
            f"  Conflicts: {len(processed['conflicts'])}"
        )
        print("  JSON-safe: YES")
        print("  CONTRACT: PASS")

    print("\n=== ALL WORKSTREAM A CONTRACT TESTS PASSED ===")


if __name__ == "__main__":
    main()