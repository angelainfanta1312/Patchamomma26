from typing import Any

from google.cloud import bigtable
from google.cloud.bigtable import row_filters

from processor.config import (
    PROJECT_ID,
    BIGTABLE_INSTANCE_ID,
    BIGTABLE_TABLE_ID,
)



class BigtableReader:
    """Reader for runtime telemetry stored in Bigtable."""

    INSTANCE_ID = BIGTABLE_INSTANCE_ID
    TABLE_NAME = BIGTABLE_TABLE_ID
    COLUMN_FAMILY = "telemetry"

    def __init__(self):
        self.client = bigtable.Client(
            project=PROJECT_ID,
            admin=False,
        )

        self.instance = self.client.instance(self.INSTANCE_ID)
        self.table = self.instance.table(self.TABLE_NAME)

    def inspect_runtime_telemetry(self, incident_id: str) -> dict[str, Any]:
        """
        Retrieve all runtime telemetry for an incident.

        Rows are keyed as:
            INC-001#001
            INC-001#002
            ...

        Results are returned in row-key order so repeated executions
        such as INC-006's EXEC-006 and EXEC-007 are preserved.
        """



        # Use a prefix filter to retrieve only this incident's rows.
        partial_rows = self.table.read_rows(
            filter_=row_filters.RowKeyRegexFilter(
                f"^{incident_id}#.*".encode("utf-8")
            )
        )

        telemetry = []

        for row in partial_rows:
            row_data = {}

            for family, columns in row.cells.items():
                for qualifier, cells in columns.items():
                    if family != self.COLUMN_FAMILY:
                        continue

                    if not cells:
                        continue

                    value = cells[-1].value.decode("utf-8")

                    row_data[qualifier.decode("utf-8")] = value

            if row_data:
                row_data["row_key"] = row.row_key.decode("utf-8")
                telemetry.append(row_data)

        telemetry.sort(key=lambda item: item["row_key"])

        v2_events = [
            event
            for event in telemetry
            if event.get("event_type") in {
                "TOOL_CALL_COMPLETED",
                "TOOL_CALL_TELEMETRY_MISSING",
            }
        ]


        return {
            "incident_id": incident_id,
            "correlation_id": (
                telemetry[0].get("correlation_id")
                if telemetry
                else None
            ),
            "events": v2_events,
            "provenance": {
                "database": "Bigtable",
                "instance": self.INSTANCE_ID,
                "table": self.TABLE_NAME,
                "column_family": self.COLUMN_FAMILY,
            },
        }