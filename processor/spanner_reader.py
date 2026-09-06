import logging

from google.cloud import spanner
from google.cloud.spanner_v1 import param_types

from processor.config import (
    PROJECT_ID,
    SPANNER_INSTANCE_ID,
    SPANNER_DATABASE_ID,
    SPANNER_STATE_TABLE,
)

logger = logging.getLogger(__name__)


class SpannerReader:
    """
    Read-only access to authoritative business state in Spanner.

    Spanner is treated as the authoritative business-state source for V2.
    This reader does not modify production/business state.
    """

    def __init__(self):
        self.client = spanner.Client(project=PROJECT_ID)

        self.instance = self.client.instance(
            SPANNER_INSTANCE_ID
        )

        self.database = self.instance.database(
            SPANNER_DATABASE_ID
        )

    def inspect_authoritative_state(self, incident_id: str) -> dict:
        """
        Retrieve authoritative account state for an incident.

        Missing state is returned as a structured result rather than
        raising an exception because absence of authoritative state
        is itself meaningful investigation evidence.
        """

        logger.info(
            "Fetching authoritative state from Spanner for %s",
            incident_id,
        )

        query = f"""
            SELECT
                incident_id,
                correlation_id,
                account_id,
                requested_action,
                authoritative_status,
                state_version,
                last_modified_at,
                last_modified_by,
                state_available,
                state_details
            FROM {SPANNER_STATE_TABLE}
            WHERE incident_id = @incident_id
        """

        params = {
            "incident_id": incident_id,
        }

        param_types_map = {
            "incident_id": param_types.STRING,
        }

        with self.database.snapshot() as snapshot:
            results = list(
                snapshot.execute_sql(
                    query,
                    params=params,
                    param_types=param_types_map,
                )
            )

        if not results:
            logger.info(
                "No authoritative state found in Spanner for %s",
                incident_id,
            )

            return {
                "incident_id": incident_id,
                "correlation_id": None,
                "state": None,
                "state_available": False,
                "provenance": {
                    "database": "Spanner",
                    "instance": SPANNER_INSTANCE_ID,
                    "database_name": SPANNER_DATABASE_ID,
                    "table": SPANNER_STATE_TABLE,
                },
            }

        row = results[0]

        state = {
            "account_id": row[2],
            "requested_action": row[3],
            "authoritative_status": row[4],
            "state_version": row[5],
            "last_modified_at": (
                row[6].isoformat()
                if row[6] is not None
                else None
            ),
            "last_modified_by": row[7],
            "state_available": row[8],
            "state_details": row[9],
        }

        response = {
            "incident_id": row[0],
            "correlation_id": row[1],
            "state": state,
            "state_available": bool(row[8]),
            "provenance": {
                "database": "Spanner",
                "instance": SPANNER_INSTANCE_ID,
                "database_name": SPANNER_DATABASE_ID,
                "table": SPANNER_STATE_TABLE,
            },
        }

        logger.info(
            "Retrieved authoritative state for %s from Spanner",
            incident_id,
        )

        return response