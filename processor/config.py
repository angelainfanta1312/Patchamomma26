import os


PROJECT_ID = os.getenv(
    "GCP_PROJECT_ID",
    "project-448c7b37-cc7c-4c20-9d9"
)

DATASET_ID = os.getenv(
    "BQ_DATASET_ID",
    "patchamomma"
)

INPUT_VIEW = os.getenv(
    "BQ_INPUT_VIEW",
    "incident_investigation_input"
)

AGENT_EXECUTION_VIEW = os.getenv(
    "BQ_AGENT_EXECUTION_VIEW",
    "agent_execution_events"
)

SPANNER_INSTANCE_ID = os.getenv(
    "SPANNER_INSTANCE_ID",
    "patchamomma-v2"
)

SPANNER_DATABASE_ID = os.getenv(
    "SPANNER_DATABASE_ID",
    "patchamomma"
)

SPANNER_STATE_TABLE = os.getenv(
    "SPANNER_STATE_TABLE",
    "account_state"
)

BIGTABLE_INSTANCE_ID = os.getenv(
    "BIGTABLE_INSTANCE_ID",
    "patchamomma-bigtable"
)

BIGTABLE_TABLE_ID = os.getenv(
    "BIGTABLE_TABLE_ID",
    "runtime_telemetry"
)
