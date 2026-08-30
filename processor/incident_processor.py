from typing import Any

import logging

logger = logging.getLogger(__name__)

class IncidentProcessor:
    """
    Converts raw incident evidence retrieved from BigQuery
    into the Workstream A -> B input contract.
    """

    def process(self, incident: dict[str, Any]) -> dict[str, Any]:
        logger.info("Processing Workstream A contract for %s",incident["incident_id"])
        """
        Normalize and validate a raw incident.

        Returns the contract that will be passed to the
        Gemini investigation layer.
        """

        processed = {
            "incident_id": incident["incident_id"],
            "corelation_id": incident["corelation_id"],
            "evidence_count": incident["evidence_count"],
            "timeline": self._normalize_timeline(incident.get("timeline", [])),
            "missing_evidence": incident.get("missing_evidence", []),
            "conflicts": self._normalize_conflicts(incident.get("conflicts", [])),
        }

        self._validate(processed)
        logger.info("Workstream A processing complete for %s", processed["incident_id"])
        return processed

    def _normalize_timeline(
        self,
        timeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Normalize timeline events into JSON-safe dictionaries.
        """

        normalized = []

        for event in timeline:
            normalized_event = dict(event)

            timestamp = normalized_event.get("timestamp")

            if timestamp is not None:
                normalized_event["timestamp"] = timestamp.isoformat()

            normalized.append(normalized_event)

        return normalized

    def _normalize_conflicts(self, conflicts: list[dict[str, Any]],) -> list[dict[str, Any]]:
        """
        Normalize conflict records into JSON-safe dictionaries.
        """

        normalized = []

        for conflict in conflicts:
            normalized_conflict = dict(conflict)

            for field in ["tool_timestamp", "system_timestamp"]:
                timestamp = normalized_conflict.get(field)

                if timestamp is not None:
                    normalized_conflict[field] = timestamp.isoformat()

            normalized.append(normalized_conflict)

        return normalized

    def _validate(self, incident: dict[str, Any]) -> None:
        """
        Validate the Workstream A -> B contract.
        """

        required_fields = [
            "incident_id",
            "corelation_id",
            "evidence_count",
            "timeline",
            "missing_evidence",
            "conflicts",
        ]

        for field in required_fields:
            if field not in incident:
                raise ValueError(
                    f"Missing required contract field: {field}"
                )

        if not isinstance(incident["timeline"], list):
            raise ValueError("timeline must be a list")

        if not isinstance(incident["missing_evidence"], list):
            raise ValueError("missing_evidence must be a list")

        if not isinstance(incident["conflicts"], list):
            raise ValueError("conflicts must be a list")