import asyncio
import json
import time

from processor.bigquery_reader import BigQueryReader
from processor.incident_processor import IncidentProcessor
from processor.gemini_investigator import GeminiInvestigator
from processor.adk.runner import investigate_incident_async
from processor.adk.workflow import create_patchamomma_workflow
from evaluation.v2_fixture_reader import V2FixtureReader


INCIDENTS = [
    "INC-001",
    "INC-002",
    "INC-003",
    "INC-004",
    "INC-005",
    "INC-006",
    "INC-007",
]


async def run_v2():
    results = {}

    fixture_reader = V2FixtureReader()
    fixture_workflow = create_patchamomma_workflow(
        evidence_reader=fixture_reader
    )

    for incident_id in INCIDENTS:
        print(f"\n{'=' * 70}")
        print(f"V2 ADK: {incident_id}")
        print(f"{'=' * 70}")

        start = time.perf_counter()

        result = await investigate_incident_async(
            incident_id,
            workflow=fixture_workflow,
        )

        elapsed_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        result["latency_ms"] = elapsed_ms

        results[incident_id] = result

        findings = result.get("deterministic_findings") or {}
        investigation = result.get("gemini_investigation")

        print("Evidence validated:", result.get("evidence_validated"))
        print(
            "Outcome:",
            findings.get("outcome_confirmation"),
        )
        print(
            "Conflicts:",
            [
                c.get("type")
                for c in findings.get("conflicts", [])
            ],
        )
        print("Latency:", elapsed_ms, "ms")
        print("\nGemini investigation:")
        print(json.dumps(
            investigation,
            indent=2,
            ensure_ascii=False,
        ))

    return results


def run_v1():
    reader = BigQueryReader()
    processor = IncidentProcessor()
    investigator = GeminiInvestigator()

    results = {}

    for incident_id in INCIDENTS:
        print(f"\n{'=' * 70}")
        print(f"V1 BASELINE: {incident_id}")
        print(f"{'=' * 70}")

        start = time.perf_counter()

        raw_incident = reader.get_incident(incident_id)
        processed_incident = processor.process(raw_incident)
        investigation = investigator.investigate(
            processed_incident
        )

        elapsed_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        results[incident_id] = {
            "input": processed_incident,
            "investigation": investigation,
            "latency_ms": elapsed_ms,
        }

        print("Latency:", elapsed_ms, "ms")
        print("\nGemini investigation:")
        print(json.dumps(
            investigation,
            indent=2,
            ensure_ascii=False,
        ))

    return results


async def main():
    print("\n" + "=" * 70)
    print("PATCHAMOMMA MATCHED V1 vs V2 ADK EVALUATION")
    print("=" * 70)

    print("\nRunning V1 baseline...")
    v1_results = run_v1()

    print("\nRunning V2 ADK...")
    v2_results = await run_v2()

    comparison = {}

    for incident_id in INCIDENTS:
        v1 = v1_results[incident_id]
        v2 = v2_results[incident_id]

        v1_inv = v1.get("investigation") or {}
        v2_inv = v2.get("gemini_investigation") or {}

        v1_findings = v1.get("input") or {}
        v2_findings = v2.get("deterministic_findings") or {}

        comparison[incident_id] = {
            "v1": {
                "latency_ms": v1.get("latency_ms"),
                "investigation": v1_inv,
            },
            "v2_adk": {
                "latency_ms": v2.get("latency_ms"),
                "investigation": v2_inv,
                "deterministic_findings": v2_findings,
            },
            "comparison": {
                "incident_id_match": (
                    v1_inv.get("incident_id")
                    == v2_findings.get("incident_id")
                ),
                "v1_conflicts": v1_inv.get(
                    "conflicts", []
                ),
                "v2_conflicts": v2_inv.get(
                    "conflicts", []
                ),
                "v1_missing_evidence": v1_inv.get(
                    "missing_evidence", []
                ),
                "v2_missing_evidence": v2_inv.get(
                    "missing_evidence", []
                ),
                "v1_possible_explanations": v1_inv.get(
                    "possible_explanations", []
                ),
                "v2_possible_explanations": v2_inv.get(
                    "possible_explanations", []
                ),
                "v1_uncertainty": v1_inv.get(
                    "uncertainty"
                ),
                "v2_uncertainty": v2_inv.get(
                    "uncertainty"
                ),
            },
        }

    output = {
        "evaluation": "Matched V1 vs V2 ADK",
        "incidents": INCIDENTS,
        "v1_baseline": v1_results,
        "v2_adk": v2_results,
        "comparison": comparison,
    }

    output_path = (
        "contracts/matched_adk_v1_evaluation_results.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "=" * 70)
    print("MATCHED EVALUATION COMPLETE")
    print("=" * 70)
    print("Results saved to:")
    print(output_path)


if __name__ == "__main__":
    asyncio.run(main())
