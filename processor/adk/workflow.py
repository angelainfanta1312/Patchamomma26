import logging
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import FunctionNode, START, Workflow

from processor.adk.investigator import patchamomma_investigator
from processor.v2_contract import validate_v2_evidence_contract
from processor.v2_deterministic import analyze_v2_evidence
from processor.v2_evidence import V2EvidenceReader


logger = logging.getLogger(__name__)


def validate_evidence(ctx: Context) -> dict[str, Any]:
    """
    Validate the V2 evidence contract produced by the evidence
    collection stage.
    """

    evidence = ctx.state["evidence"]

    validate_v2_evidence_contract(evidence)

    logger.info(
        "ADK workflow evidence contract validated for %s",
        ctx.state["incident_id"],
    )

    ctx.state["evidence_validated"] = True

    return {
        "validated": True,
    }


def deterministic_analysis(ctx: Context) -> dict[str, Any]:
    """
    Perform deterministic analysis over the validated V2 evidence.
    """

    evidence = ctx.state["evidence"]

    findings = analyze_v2_evidence(evidence)

    ctx.state["deterministic_findings"] = findings

    logger.info(
        "ADK workflow deterministic analysis completed for %s",
        ctx.state["incident_id"],
    )

    return {
        "findings": findings,
    }


async def run_gemini_investigator(
    ctx: Context,
) -> dict[str, Any]:
    """
    Invoke the ADK Gemini investigator using the evidence and
    deterministic findings already produced by the workflow.
    """

    evidence = ctx.state["evidence"]

    deterministic_findings = ctx.state[
        "deterministic_findings"
    ]

    investigation_context = {
        "incident_id": ctx.state["incident_id"],
        "evidence": evidence,
        "deterministic_findings": deterministic_findings,
    }

    logger.info(
        "ADK workflow invoking Gemini investigator for %s",
        ctx.state["incident_id"],
    )

    result = await ctx.run_node(
        patchamomma_investigator,
        node_input=investigation_context,
        override_isolation_scope="",
    )

    ctx.state["gemini_investigation"] = result

    return {
        "investigation": result,
    }


def create_patchamomma_workflow(
    evidence_reader=None,
) -> Workflow:
    """
    Create a Patchamomma ADK investigation workflow.

    Production uses V2EvidenceReader.

    Tests may inject a fixture-backed evidence reader so the
    workflow can be tested without live AlloyDB connectivity.
    """

    reader = evidence_reader or V2EvidenceReader()

    def collect_evidence(
        ctx: Context,
    ) -> dict[str, Any]:
        """
        Collect the complete V2 evidence package.
        """

        incident_id = ctx.state["incident_id"]

        logger.info(
            "ADK workflow collecting evidence for %s",
            incident_id,
        )

        evidence = reader.inspect_incident(
            incident_id
        )

        ctx.state["evidence"] = evidence

        return {
            "incident_id": incident_id,
            "evidence": evidence,
        }

    collect_evidence_node = FunctionNode(
        func=collect_evidence,
        name="collect_evidence",
    )

    validate_evidence_node = FunctionNode(
        func=validate_evidence,
        name="validate_evidence",
    )

    deterministic_analysis_node = FunctionNode(
        func=deterministic_analysis,
        name="deterministic_analysis",
    )

    gemini_investigator_node = FunctionNode(
        func=run_gemini_investigator,
        name="run_gemini_investigator",
        rerun_on_resume=True,
    )

    return Workflow(
        name="patchamomma_investigation_workflow",
        description=(
            "Orchestrates Patchamomma evidence collection, "
            "validation, deterministic analysis, and Gemini "
            "investigation."
        ),
        edges=[
            (START, collect_evidence_node),
            (
                collect_evidence_node,
                validate_evidence_node,
            ),
            (
                validate_evidence_node,
                deterministic_analysis_node,
            ),
            (
                deterministic_analysis_node,
                gemini_investigator_node,
            ),
        ],
    )


# Production workflow.
#
# Uses the real V2EvidenceReader and therefore the four
# production evidence sources.
patchamomma_workflow = create_patchamomma_workflow()