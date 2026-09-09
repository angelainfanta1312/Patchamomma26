import json
from typing import Any

from google.cloud.alloydbconnector import Connector
from processor.config import PROJECT_ID




class AlloyDBReader:
    """Reader for tool execution evidence stored in AlloyDB."""

    INSTANCE_URI = (
        f"projects/{PROJECT_ID}/locations/asia-south1/"
        "clusters/patchamomma-alloydb/instances/primary"
    )

    DATABASE_NAME = "postgres"
    TABLE_NAME = "tool_execution"

    def __init__(self, user: str = "aiei-run@project-448c7b37-cc7c-4c20-9d9.iam"):
        self.user = user
        self.connector = Connector()

    def inspect_tool_execution(self, incident_id: str) -> dict[str, Any]:
        """
        Retrieve all tool executions for an incident.

        Results are ordered by started_at so repeated executions,
        such as INC-006's EXEC-006 and EXEC-007, are preserved.
        """

        conn = None

        try:
            conn = self.connector.connect(
                self.INSTANCE_URI,
                "pg8000",
                user=self.user,
                db=self.DATABASE_NAME,
                enable_iam_auth=True,
                ip_type="PSC",
            )

            cursor = conn.cursor()

            query = f"""
                SELECT
                    execution_id,
                    incident_id,
                    correlation_id,
                    started_at,
                    completed_at,
                    tool_name,
                    request,
                    response,
                    status,
                    duration_ms,
                    error_details
                FROM {self.TABLE_NAME}
                WHERE incident_id = %s
                ORDER BY started_at ASC, execution_id ASC
            """

            cursor.execute(query, (incident_id,))
            rows = cursor.fetchall()

            executions = []

            for row in rows:
                (
                    execution_id,
                    row_incident_id,
                    correlation_id,
                    started_at,
                    completed_at,
                    tool_name,
                    request,
                    response,
                    status,
                    duration_ms,
                    error_details,
                ) = row

                executions.append(
                    {
                        "execution_id": execution_id,
                        "incident_id": row_incident_id,
                        "correlation_id": correlation_id,
                        "started_at": (
                            started_at.isoformat()
                            if started_at is not None
                            else None
                        ),
                        "completed_at": (
                            completed_at.isoformat()
                            if completed_at is not None
                            else None
                        ),
                        "tool_name": tool_name,
                        "request": self._normalize_json(request),
                        "response": self._normalize_json(response),
                        "status": status,
                        "duration_ms": duration_ms,
                        "error_details": error_details,
                    }
                )

            return {
                "incident_id": incident_id,
                "correlation_id": (
                    executions[0].get("correlation_id")
                    if executions
                    else None
                ),
                "executions": executions,
                "execution_count": len(executions),
                "provenance": {
                    "database": "AlloyDB",
                    "instance": "primary",
                    "cluster": "patchamomma-alloydb",
                    "database_name": self.DATABASE_NAME,
                    "table": self.TABLE_NAME,
                },
            }

        finally:
            if conn is not None:
                conn.close()
                
    def close(self) -> None:
        """Close the AlloyDB connector."""
        self.connector.close()

    @staticmethod
    def _normalize_json(value: Any) -> Any:
        """Normalize PostgreSQL JSON/JSONB values."""

        if value is None:
            return None

        if isinstance(value, (dict, list)):
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value

    