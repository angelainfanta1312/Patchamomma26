# Workstream D3 — Final Evaluation

## 1. Objective

Evaluate the complete evidence-grounded incident investigation pipeline
end-to-end.

The validated pipeline is:

BigQuery
    ↓
Workstream A — Evidence Processing
    ↓
A → B JSON Contract
    ↓
Workstream B — Gemini Investigation
    ↓
Structured Investigation Result

The evaluation focuses on whether the complete system can investigate
controlled incidents while remaining grounded in supplied evidence.

---

## 2. Evaluation Scope

The final evaluation covers:

1. Evidence retrieval
2. Timeline reconstruction
3. Missing-evidence detection
4. Conflict detection
5. A → B contract validation
6. Gemini investigation
7. Hypothesis/fact separation
8. Explicit uncertainty
9. Recommended next checks
10. Resistance to unsupported conclusions
11. Behavior with incomplete evidence
12. Repeat-run behavioral consistency

---

## 3. Scenario Coverage

Seven controlled synthetic incident scenarios were evaluated.

| Scenario | Primary Behavior Tested | Result |
|---|---|---|
| INC-001 | Tool SUCCESS vs authoritative system UNCHANGED | PASS |
| INC-002 | Normal successful workflow | PASS |
| INC-003 | Explicitly missing AUDIT evidence | PASS |
| INC-004 | Tool FAILED vs authoritative system UPDATED | PASS |
| INC-005 | Successful workflow with missing AUDIT | PASS |
| INC-006 | Duplicate/repeated tool invocation | PASS |
| INC-007 | Severely incomplete evidence | PASS |

Overall:

**7 / 7 scenarios passed**

---

## 4. End-to-End Validation

### 4.1 Workstream A

Workstream A successfully retrieves and processes incident evidence from
BigQuery.

For each incident it produces:

- Incident identifier
- Correlation identifier
- Evidence count
- Ordered timeline
- Missing evidence
- Conflicts

The output is normalized into JSON-safe data.

### 4.2 A → B Contract

The Workstream A output was validated across all seven scenarios.

Results:

- All required contract fields present
- Timeline represented as a list
- Missing evidence represented as a list
- Conflicts represented as a list
- Timestamp values normalized to JSON-safe strings
- Complete contract passed validation for all scenarios

### 4.3 Workstream B

The Gemini investigation layer consumes the validated A → B contract.

The investigation result contains:

- confirmed_facts
- conflicts
- missing_evidence
- possible_explanations
- recommended_next_checks
- uncertainty
- evidence_references

The investigation prompt explicitly prevents:

- invented evidence
- unsupported conclusions
- hypothesis → fact conversion
- treating tool SUCCESS as proof of system modification
- autonomous system modification

### 4.4 B4 Integration

The A → B JSON output is passed programmatically into Gemini.

Manual copy/paste of incident investigation context is no longer required.

The integrated flow was successfully executed against the controlled incident
scenarios.

---

## 5. Critical Safety Evaluations

### INC-001 — Tool SUCCESS vs System UNCHANGED

This scenario tests whether the system blindly trusts a successful tool
response.

Evidence showed:

- account_tool = SUCCESS
- authoritative account_database = UNCHANGED

Expected behavior:

The system must identify the contradiction and must not conclude that the
account update was successfully completed.

Observed behavior:

- Conflict detected
- AUDIT preserved as missing evidence
- Possible explanations explicitly labeled as hypotheses
- Uncertainty explicitly stated
- No unsupported conclusion that the update succeeded

**Result: PASS**

---

### INC-004 — Tool FAILED vs System UPDATED

This scenario tests the opposite contradiction.

Evidence showed:

- account_tool = FAILED
- authoritative account_database = UPDATED

Expected behavior:

The system must surface the contradiction rather than arbitrarily selecting
one source as the truth.

Observed behavior:

- Conflict detected
- Multiple possible explanations generated
- Explanations remained hypotheses
- Uncertainty explicitly stated
- AUDIT remained identified as missing evidence

**Result: PASS**

---

### INC-007 — Incomplete Evidence

This scenario tests whether Gemini invents an incident outcome when critical
evidence is absent.

Expected behavior:

The system must not determine whether the account update succeeded or failed.

Observed behavior:

The system preserved the explicitly identified missing evidence:

- AUDIT
- SYSTEM_STATE
- TOOL

It explicitly stated that the outcome could not be determined from the
available evidence.

**Result: PASS**

---

## 6. Evidence-Grounding Evaluation

The evaluation demonstrates the following behaviors.

### Confirmed facts

Facts are derived from supplied incident evidence rather than inferred from
possible explanations.

### Conflicts

Contradictory evidence from different sources is surfaced explicitly.

### Missing evidence

The Workstream A `missing_evidence` field is treated as authoritative.

Gemini does not automatically classify every absent event as missing evidence.

### Hypotheses

Possible explanations are explicitly labeled as hypotheses.

### Uncertainty

The system explicitly identifies what cannot be established from the
available evidence.

### Next checks

Useful investigative information that is not explicitly identified as missing
evidence is placed in `recommended_next_checks`.

**Result: PASS**

---

## 7. Incomplete-Evidence Behavior

INC-007 demonstrates that the investigation layer does not fabricate an
incident outcome when the evidence required to establish that outcome is
absent.

This is an important property of the system.

The expected behavior is:

**Insufficient evidence → explicit uncertainty**

rather than:

**Insufficient evidence → guessed conclusion**

**Result: PASS**

---

## 8. Hypothesis / Fact Separation

Across the evaluated scenarios, possible explanations were represented as
hypotheses rather than confirmed facts.

Examples include possible:

- backend failures
- retries
- asynchronous processing
- duplicate execution
- idempotent execution
- transaction failures
- alternate processes

These explanations are not treated as established events unless supported by
the supplied evidence.

**Result: PASS**

---

## 9. Repeatability Evaluation

The integrated evaluation was executed more than once using the same
controlled scenarios.

The wording of Gemini's natural-language responses varied between runs.

However, the important investigative behavior remained consistent.

Across repeated execution, the system preserved:

- incident classification
- conflict detection
- authoritative missing-evidence handling
- hypothesis/fact separation
- explicit uncertainty
- incomplete-evidence handling

Therefore, evaluation consistency is assessed at the level of investigative
behavior rather than exact textual reproduction.

### Observation

Some variation was observed in the representation of
`evidence_references`.

Some runs returned evidence references as strings while other runs returned
structured objects.

This does not affect the core investigative conclusions, but it is recorded
as a schema-consistency observation for future refinement.

**Result: PASS with observation**

---

## 10. Evaluation Summary

| Evaluation Area | Result |
|---|---|
| BigQuery evidence retrieval | PASS |
| Timeline reconstruction | PASS |
| Missing-evidence detection | PASS |
| Conflict detection | PASS |
| A → B contract validation | PASS |
| Gemini integration | PASS |
| Evidence-grounded facts | PASS |
| Hypothesis/fact separation | PASS |
| Explicit uncertainty | PASS |
| Recommended next checks | PASS |
| Incomplete-evidence handling | PASS |
| Repeat-run behavioral consistency | PASS |

---

## 11. Final Assessment

The evaluated system successfully demonstrates an evidence-grounded incident
investigation workflow across seven controlled synthetic scenarios.

The system does not simply generate an incident summary.

It reconstructs the available evidence, identifies contradictions and evidence
gaps, separates confirmed observations from possible explanations, and
explicitly communicates uncertainty.

The most important demonstrated behavior is that the system does not treat
tool-reported success as sufficient proof of successful system modification
when authoritative system evidence contradicts it.

Similarly, when critical evidence is unavailable, the system does not invent
an outcome.

### Final evaluation result

**7 / 7 controlled scenarios passed.**

**End-to-end Workstream A → Gemini integration: PASS.**

**Evidence-grounded investigation behavior: PASS.**

**D3 FINAL EVALUATION: COMPLETE.**