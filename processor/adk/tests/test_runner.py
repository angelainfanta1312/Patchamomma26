import asyncio

from processor.adk.runner import investigate_incident_async
from processor.adk.tests.test_workflow import (
    FIXTURE_EVIDENCE,
    test_workflow,
)


async def main():
    result = await investigate_incident_async(
        "INC-001",
        workflow=test_workflow,
    )

    print("\n=== PATCHAMOMMA ADK RUNNER TEST ===")

    print("\nIncident:")
    print(result["incident_id"])

    print("\nEvidence validated:")
    print(result["evidence_validated"])

    findings = result["deterministic_findings"]

    print("\nOutcome:")
    print(findings.get("outcome_confirmation"))

    print("\nConflicts:")
    for conflict in findings.get("conflicts", []):
        print(f"  - {conflict}")

    print("\nGemini investigation:")
    print(result["gemini_investigation"])

    print("\n=== RUNNER TEST COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())
