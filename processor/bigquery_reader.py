from google.cloud import bigquery

from processor.config import PROJECT_ID, DATASET_ID, INPUT_VIEW, AGENT_EXECUTION_VIEW

import logging

logger = logging.getLogger(__name__)

class BigQueryReader:
    def __init__(self):
        self.client = bigquery.Client(project=PROJECT_ID)
    
    def list_incidents(self) -> list[str]:
        logger.info("Fetching incident IDs from BigQuery")
        query = f"""
            SELECT DISTINCT incident_id
            FROM `{PROJECT_ID}.{DATASET_ID}.{INPUT_VIEW}`
            WHERE incident_id IS NOT NULL
            ORDER BY incident_id
        """

        results = self.client.query(query).result()
        
        return [row["incident_id"] for row in results]
    
    def get_incident(self, incident_id: str) -> dict:
        logger.info("Fetching incident evidence for %s", incident_id)
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
        logger.info("Retrieved incident %s from BigQuery", incident_id)
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
    
    def inspect_agent_execution(self, incident_id: str) -> dict:
        logger.info(
            "Fetching agent execution evidence for %s",
            incident_id
        )

        query = f"""
        SELECT
            incident_id,
            corelation_id,
            sequence_number,
            timestamp,
            source,
            event_type,
            actor,
            action,
            status,
            details
        FROM `{PROJECT_ID}.{DATASET_ID}.{AGENT_EXECUTION_VIEW}`
        WHERE incident_id = @incident_id
        ORDER BY sequence_number
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "incident_id",
                    "STRING",
                    incident_id
                )
            ]
        )

        results = list(
            self.client.query(
                query,
                job_config=job_config
            ).result()
        )

        if not results:
            raise ValueError(
                f"Agent execution evidence not found: {incident_id}"
            )

        events = []

        for row in results:
            timestamp = row["timestamp"]
            events.append(
                {
                    "sequence_number": row["sequence_number"],
                    "timestamp": (
                        timestamp.isoformat()
                        if timestamp is not None
                        else None
                    ),
                    "source": row["source"],
                    "event_type": row["event_type"],
                    "actor": row["actor"],
                    "action": row["action"],
                    "status": row["status"],
                    "details": row["details"],
                }
            )
            
        return {
            "incident_id": results[0]["incident_id"],
            "correlation_id": results[0]["corelation_id"],
            "events": events,
            "provenance": {
                "database": "BigQuery",
                "dataset": DATASET_ID,
                "view": AGENT_EXECUTION_VIEW,
            }
        }