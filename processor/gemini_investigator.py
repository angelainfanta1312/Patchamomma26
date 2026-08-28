import json
from typing import Any

from google import genai


INVESTIGATION_PROMPT = """
Analyze the incident investigation context provided below.

Your task is to perform an evidence-grounded investigation and return a structured investigation result.

The investigation must:

1. Identify only facts directly supported by the provided evidence.
2. Interpret the timeline based only on the supplied events and their timestamps.
3. Identify and explain conflicts between evidence sources.
4. Identify missing evidence that prevents stronger conclusions.
5. Provide possible explanations for the observed situation, clearly labeling them as hypotheses rather than facts.
6. Recommend specific next checks that could resolve uncertainty or investigate the incident further.
7. Provide evidence references showing which supplied evidence supports the findings.
8. State uncertainty explicitly wherever the evidence is insufficient.

Important rules:

- Do not invent evidence or events.
- Do not assume that an action occurred just because a tool reported SUCCESS.
- If a tool reports SUCCESS but the system state is UNCHANGED, treat this as a conflict and do not conclude that the intended action was successfully completed.
- Do not fill gaps in the evidence with assumptions.
- Do not turn a possible explanation into a confirmed fact.
- If something cannot be established from the evidence, say so explicitly.

Missing evidence handling:

The `missing_evidence` field in the investigation context is authoritative.

Copy only explicitly identified missing evidence into the output `missing_evidence` field.

If the input `missing_evidence` array is empty, the output `missing_evidence` array MUST also be empty.

Do not infer that information is missing merely because it is not present in the supplied timeline.

Information that could be useful for further investigation but is not explicitly identified as missing must be placed in `recommended_next_checks`, not `missing_evidence`.

Return ONLY valid JSON.

The JSON must follow exactly this structure:

{
  "incident_id": "<incident_id>",
  "confirmed_facts": [],
  "conflicts": [],
  "missing_evidence": [],
  "possible_explanations": [],
  "recommended_next_checks": [],
  "uncertainty": "",
  "evidence_references": []
}

Requirements for the JSON:

- Preserve the incident_id from the investigation context.
- Each array must contain only information supported by the supplied evidence.
- Possible explanations must be clearly expressed as hypotheses.
- The uncertainty field must explicitly state what cannot be established from the available evidence.
- Evidence references must identify the relevant supplied evidence supporting the findings.
- Do not add fields that are not present in the required structure.
- Do not omit any required field.
"""


class GeminiInvestigator:
    """
    Workstream B Gemini investigation layer.

    Receives the validated Workstream A -> B contract
    and produces an evidence-grounded investigation result.
    """

    def __init__(
        self,
        project: str = "project-448c7b37-cc7c-4c20-9d9",
        location: str = "global",
        model: str = "gemini-3.6-flash",
    ):
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        self.model = model

    def investigate(self, incident_context: dict[str, Any]) -> dict[str, Any]:
        """
        Send the validated Workstream A contract to Gemini
        and return the structured investigation result.
        """

        context_json = json.dumps(
            incident_context,
            indent=2,
            ensure_ascii=False,
        )

        prompt = (
            INVESTIGATION_PROMPT
            + "\n\nInvestigation context:\n"
            + context_json
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        text = response.text.strip()

        # Remove accidental markdown fences if the model adds them.
        if text.startswith("```json"):
            text = text[7:]

        if text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        return json.loads(text)