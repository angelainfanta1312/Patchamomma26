from dataclasses import dataclass
from typing import Any


@dataclass
class IncidentInvestigationInput:
    incident_id: str
    corelation_id: str
    evidence_count: int
    timeline: list[dict[str, Any]]
    missing_evidence: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]