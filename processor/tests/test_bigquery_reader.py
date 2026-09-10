from processor.bigquery_reader import BigQueryReader


def main():
    reader = BigQueryReader()

    incident = reader.get_incident("INC-003")

    print("\n=== INCIDENT ===")
    print("Incident ID:", incident["incident_id"])
    print("corelation ID:", incident["corelation_id"])
    print("Evidence count:", incident["evidence_count"])

    print("\n=== TIMELINE ===")
    for event in incident["timeline"]:
        print(event)

    print("\n=== MISSING EVIDENCE ===")
    print(incident["missing_evidence"])

    print("\n=== CONFLICTS ===")
    print(incident["conflicts"])


if __name__ == "__main__":
    main()