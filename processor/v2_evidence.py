import logging

from processor.bigquery_reader import BigQueryReader
from processor.spanner_reader import SpannerReader
from processor.v2_contract import validate_v2_evidence_contract

logger = logging.getLogger(__name__)


class V2EvidenceReader:
    """
    Combines independent evidence sources for V2 investigation.

    BigQuery:
        Agent/user execution evidence.

    Spanner:
        Authoritative business state.

    This class is read-only.
    """

    def __init__(self):
        self.bigquery = BigQueryReader()
        self.spanner = SpannerReader()

    def inspect_incident(self, incident_id: str) -> dict:
        logger.info(
            "Collecting V2 evidence for %s",
            incident_id,
        )

        agent_execution = self.bigquery.inspect_agent_execution(
            incident_id
        )

        authoritative_state = (
            self.spanner.inspect_authoritative_state(
                incident_id
            )
        )

        evidence = {
            "incident_id": incident_id,
            "corelation_id": agent_execution["correlation_id"],
            "agent_execution": agent_execution,
            "authoritative_state": authoritative_state,
        }

        validate_v2_evidence_contract(evidence)

        return evidence