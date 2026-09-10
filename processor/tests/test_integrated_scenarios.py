import json

from processor.bigquery_reader import BigQueryReader
from processor.incident_processor import IncidentProcessor
from processor.gemini_investigator import GeminiInvestigator


INCIDENTS = [
    "INC-001",
    "INC-002",
    "INC-003",
    "INC-004",
    "INC-005",
    "INC-006",
    "INC-007",
]


def main():
    reader = BigQueryReader()
    processor = IncidentProcessor()
    investigator = GeminiInvestigator()

    results = {}

    for incident_id in INCIDENTS:
        print(f"\n{'=' * 60}")
        print(f"INVESTIGATING {incident_id}")
        print(f"{'=' * 60}")

        raw_incident = reader.get_incident(incident_id)

        processed_incident = processor.process(raw_incident)

        investigation = investigator.investigate(processed_incident)

        results[incident_id] = {
            "input": processed_incident,
            "investigation": investigation,
        }

        print(json.dumps(investigation, indent=2, ensure_ascii=False))

    with open(
        "./contracts/integrated_evaluation_results.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "=" * 60)
    print("INTEGRATED EVALUATION COMPLETE")
    print("=" * 60)
    print("Results saved to: integrated_evaluation_results.json")


if __name__ == "__main__":
    main()