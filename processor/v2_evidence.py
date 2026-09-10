import logging

from processor.bigquery_reader import BigQueryReader
from processor.spanner_reader import SpannerReader
from processor.alloydb_reader import AlloyDBReader
from processor.bigtable_reader import BigtableReader
from processor.v2_contract import validate_v2_evidence_contract

logger = logging.getLogger(__name__)


class V2EvidenceReader:
    def __init__(
        self,
        bigquery_reader=None,
        spanner_reader=None,
        alloydb_reader=None,
        bigtable_reader=None,
    ):
        self.bigquery = bigquery_reader or BigQueryReader()
        self.spanner = spanner_reader or SpannerReader()
        self.alloydb = alloydb_reader or AlloyDBReader()
        self.bigtable = bigtable_reader or BigtableReader()

    def inspect_incident(self, incident_id: str) -> dict:
        logger.info("Collecting V2 evidence for %s", incident_id)

        agent_execution = self.bigquery.inspect_agent_execution(
            incident_id
        )

        authoritative_state = (
            self.spanner.inspect_authoritative_state(
                incident_id
            )
        )

        if self.alloydb is None:
            raise RuntimeError(
                "AlloyDB reader has not been configured"
            )

        if self.bigtable is None:
            raise RuntimeError(
                "Bigtable reader has not been configured"
            )

        tool_execution = (
            self.alloydb.inspect_tool_execution(
                incident_id
            )
        )

        runtime_telemetry = (
            self.bigtable.inspect_runtime_telemetry(
                incident_id
            )
        )

        evidence = {
            "incident_id": incident_id,
            "correlation_id": agent_execution["correlation_id"],
            "agent_execution": agent_execution,
            "tool_execution": tool_execution,
            "authoritative_state": authoritative_state,
            "runtime_telemetry": runtime_telemetry,
        }

        validate_v2_evidence_contract(evidence)

        return evidence