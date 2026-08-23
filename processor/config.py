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