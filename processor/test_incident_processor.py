from processor.bigquery_reader import BigQueryReader
from processor.incident_processor import IncidentProcessor


def main():
    reader = BigQueryReader()
    processor = IncidentProcessor()

    raw_incident = reader.get_incident("INC-001")

    processed_incident = processor.process(raw_incident)

    print("\n=== PROCESSED INCIDENT ===")
    print(f"Incident ID: {processed_incident['incident_id']}")
    print(f"Corelation ID: {processed_incident['corelation_id']}")
    print(f"Evidence count: {processed_incident['evidence_count']}")

    print("\n=== TIMELINE ===")
    for event in processed_incident["timeline"]:
        print(event)

    print("\n=== MISSING EVIDENCE ===")
    print(processed_incident["missing_evidence"])

    print("\n=== CONFLICTS ===")
    print(processed_incident["conflicts"])


if __name__ == "__main__":
    main()