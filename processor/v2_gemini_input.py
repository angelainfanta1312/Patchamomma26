import json
import logging

from processor.v2_deterministic import analyze_v2_evidence

logger = logging.getLogger(__name__)


def build_gemini_input(evidence: dict) -> dict:
    """
    Build the structured input sent to Gemini.

    Gemini receives:
      1. The original four-source evidence.
      2. Deterministic findings derived from that evidence.

    This function does not ask Gemini to determine facts.
    """

    deterministic_result = analyze_v2_evidence(evidence)

    gemini_input = {
        "incident_id": evidence["incident_id"],
        "correlation_id": evidence["correlation_id"],

        "evidence": {
            "agent_execution": evidence["agent_execution"],
            "tool_execution": evidence["tool_execution"],
            "authoritative_state": evidence["authoritative_state"],
            "runtime_telemetry": evidence["runtime_telemetry"],
        },

        "deterministic_findings": deterministic_result,

        "investigation_rules": [
            "Treat evidence from each source according to its declared meaning.",
            "BigQuery represents agent execution evidence.",
            "AlloyDB represents tool execution evidence.",
            "Spanner represents authoritative business state.",
            "Bigtable represents runtime telemetry.",
            "Do not treat tool SUCCESS as proof that business state changed.",
            "Do not treat tool FAILURE as proof that business state remained unchanged.",
            "Do not treat runtime telemetry as authoritative business state.",
            "Do not invent missing evidence.",
            "Do not invent root causes, motivations, or causal explanations.",
            "Preserve explicit conflicts between evidence sources.",
            "Preserve uncertainty when the available evidence cannot establish an outcome.",
        ],
    }

    logger.info(
        "Built V2 Gemini input for %s",
        evidence["incident_id"],
    )

    return gemini_input


def build_gemini_prompt(evidence: dict) -> str:
    """
    Convert the structured V2 Gemini input into a JSON prompt.

    JSON is used so that the evidence structure and provenance
    remain explicit and machine-readable.
    """

    gemini_input = build_gemini_input(evidence)

    instruction = """
You are investigating a distributed AI-agent incident.

Analyze ONLY the evidence supplied below.

The deterministic findings are precomputed evidence observations.
Do not override them without direct supporting evidence.

Your investigation must:

1. Separate confirmed facts from hypotheses.
2. Preserve conflicts between evidence sources.
3. Preserve missing evidence.
4. Never invent evidence, causes, motivations, or system behavior.
5. Treat Spanner authoritative state as the source of truth for business state.
6. Treat AlloyDB as evidence of what the tool reported.
7. Treat BigQuery as evidence of what the agent executed.
8. Treat Bigtable as runtime telemetry, not authoritative business state.
9. Explicitly distinguish tool execution outcome from business-state outcome.
10. State uncertainty whenever the evidence does not establish an outcome.

Return:
- confirmed_facts
- conflicts
- missing_evidence
- possible_explanations
- recommended_next_checks
- uncertainty
- evidence_references

Possible explanations must be explicitly labeled as hypotheses and must be grounded in the supplied evidence.
"""

    return (
        instruction.strip()
        + "\n\nEVIDENCE PACKAGE:\n"
        + json.dumps(
            gemini_input,
            indent=2,
            default=str,
        )
    )