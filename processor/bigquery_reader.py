from google.cloud import bigquery

from processor.config import PROJECT_ID, DATASET_ID, INPUT_VIEW


class BigQueryReader:
    def __init__(self):
        self.client = bigquery.Client(project=PROJECT_ID)

    def get_incident(self, incident_id: str) -> dict:
        query = f"""
            SELECT
                incident_id,
                corelation_id,
                evidence_count,
                timeline,
                missing_evidence,
                conflicts
            FROM `{PROJECT_ID}.{DATASET_ID}.{INPUT_VIEW}`
            WHERE incident_id = @incident_id
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "incident_id",
                    "STRING",
                    incident_id,
                )
            ]
        )

        results = list(
            self.client.query(
                query,
                job_config=job_config,
            ).result()
        )

        if not results:
            raise ValueError(f"Incident not found: {incident_id}")

        row = results[0]

        return {
            "incident_id": row["incident_id"],
            "corelation_id": row["corelation_id"],
            "evidence_count": row["evidence_count"],
            "timeline": [dict(item) for item in row["timeline"]],
            "missing_evidence": [
                dict(item) for item in row["missing_evidence"]
            ],
            "conflicts": [
                dict(item) for item in row["conflicts"]
            ],
        }