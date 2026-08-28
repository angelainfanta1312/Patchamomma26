import json

from processor.bigquery_reader import BigQueryReader
from processor.incident_processor import IncidentProcessor
from processor.gemini_investigator import GeminiInvestigator


def main():
    reader = BigQueryReader()
    processor = IncidentProcessor()
    investigator = GeminiInvestigator()

    raw_incident = reader.get_incident("INC-001")

    processed_incident = processor.process(raw_incident)

    investigation = investigator.investigate(processed_incident)

    print("=== GEMINI INVESTIGATION ===")
    print(json.dumps(investigation, indent=2, ensure_ascii=False))

    print("\n=== B4 INTEGRATION TEST PASSED ===")


if __name__ == "__main__":
    main()