# Mode: second-opinion — Adversarial Re-Evaluation

**Trigger:** `/claudemed second-opinion`
**Goal:** Re-examine the most recent consultation with maximum adversarial rigor. Steel-man arguments against the top diagnosis. Deliberately search for what was missed, minimized, or assumed.

## 1. Load Prior Analysis

Read the most recent report from `reports/`. If multiple cases, ask which one.

## 2. Devil's Advocate Protocol

Assign two adversarial roles:

### The Challenger
Argues aggressively against the top diagnosis:
- "What if this is actually [alternative]?"
- "What finding was explained away that could instead point to [serious diagnosis]?"
- "What is the base rate of this diagnosis in a patient with this demographic profile?"
- "What serious diagnosis has the most symptom overlap with what was proposed?"

### The Skeptic  
Questions the methodology:
- "Were any cognitive biases active? (anchoring, availability, premature closure)"
- "Was confirmatory evidence over-weighted relative to disconfirming evidence?"
- "Was the patient's history taken at face value when it should have been questioned?"
- "Were drug side effects / iatrogenic causes considered?"
- "Was a psychosomatic or functional diagnosis considered AND appropriately included/excluded?"

## 3. Bias Check

Explicitly name and assess each cognitive bias:

| Bias | Present? | Impact |
|------|----------|--------|
| Anchoring (fixated on first diagnosis) | [Y/N] | [Low/Med/High] |
| Availability (recent similar case) | [Y/N] | [Low/Med/High] |
| Premature closure (stopped at first fit) | [Y/N] | [Low/Med/High] |
| Framing (patient's narrative shaped diagnosis) | [Y/N] | [Low/Med/High] |
| Confirmation bias (sought supporting evidence only) | [Y/N] | [Low/Med/High] |
| Representation (pattern-matched to textbook case) | [Y/N] | [Low/Med/High] |
| Omission bias (didn't order because result might complicate things) | [Y/N] | [Low/Med/High] |

## 4. The "Can't Miss" Audit

For the presenting complaint, list the 3–5 diagnoses that are most dangerous to miss — regardless of probability — and confirm each was explicitly considered and either included or excluded with justification.

```
## Can't Miss Audit

| Dangerous Diagnosis | Considered? | Evidence For | Evidence Against | Status |
|---------------------|------------|-------------|-----------------|--------|
| [Dx] | [Y/N] | [findings] | [findings] | [Included / Excluded / Needs test] |
```

## 5. Revised Assessment

After adversarial review:

```markdown
## Second Opinion Verdict

### What the First Analysis Got Right
[Honest acknowledgment of what was well-reasoned]

### What Was Underweighted
[Diagnoses or findings that deserve higher probability after challenge]

### Recommended Changes to Differential
| Diagnosis | Prior Confidence | Revised Confidence | Reason |
|-----------|-----------------|-------------------|--------|
| [Dx] | [X.X]/5 | [X.X]/5 | [why changed] |

### Additional Tests Recommended
[Tests not previously ordered that the adversarial review reveals are needed]

### Overall Verdict
[One of:]
- "Prior analysis stands — adversarial review did not surface significant concerns."
- "Prior analysis is partially revised — [specific changes]."
- "Prior analysis requires significant revision — [what changed and why]."
```

## 6. Update Tracker

Mark the case status as `Updated` in `data/cases.md`. Append second-opinion notes to the existing report.
