import logging

from processor.bigquery_reader import BigQueryReader
from processor.spanner_reader import SpannerReader
from processor.bigtable_reader import BigtableReader
from processor.alloydb_reader import AlloyDBReader

logger = logging.getLogger(__name__)


def get_agent_execution(incident_id: str) -> dict:
    """
    Retrieve agent execution evidence for an incident from BigQuery.

    Use this tool to determine what the AI agent actually executed,
    including agent events, actions, sequence, and correlation ID.
    BigQuery evidence represents agent execution behavior.
    """
    logger.info(
        "ADK tool: fetching BigQuery agent execution for %s",
        incident_id,
    )

    reader = BigQueryReader()
    return reader.inspect_agent_execution(incident_id)


def get_authoritative_state(incident_id: str) -> dict:
    """
    Retrieve authoritative business state for an incident from Spanner.

    Use this tool to determine whether the requested business-state
    change actually occurred. Spanner is authoritative for business state.
    """
    logger.info(
        "ADK tool: fetching Spanner authoritative state for %s",
        incident_id,
    )

    reader = SpannerReader()
    return reader.inspect_authoritative_state(incident_id)


def get_runtime_telemetry(incident_id: str) -> dict:
    """
    Retrieve runtime telemetry for an incident from Bigtable.

    Use this tool to inspect runtime behavior such as execution IDs,
    retries, latency, timestamps, and telemetry status.

    Bigtable telemetry is supporting operational evidence and is NOT
    authoritative business state.
    """
    logger.info(
        "ADK tool: fetching Bigtable runtime telemetry for %s",
        incident_id,
    )

    reader = BigtableReader()
    return reader.inspect_runtime_telemetry(incident_id)


def get_tool_execution(incident_id: str) -> dict:
    """
    Retrieve tool execution evidence for an incident from AlloyDB.

    Use this tool to determine what the tool reported, including
    execution IDs, status, request, response, duration, and errors.

    AlloyDB represents tool execution evidence.
    Tool SUCCESS is not proof that authoritative business state changed.
    Tool FAILURE is not proof that authoritative business state remained unchanged.
    """
    logger.info(
        "ADK tool: fetching AlloyDB tool execution for %s",
        incident_id,
    )

    reader = AlloyDBReader()

    try:
        return reader.inspect_tool_execution(incident_id)
    finally:
        reader.close()