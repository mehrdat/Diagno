# Mode: patterns — Pattern Analysis Across Cases

**Trigger:** `/claudemed patterns`
**Goal:** Identify patterns, recurring themes, and diagnostic insights across all tracked cases. Useful for tracking chronic conditions over time, identifying missed diagnoses, or finding systemic issues.

## 1. Load All Cases

Read `data/cases.md` for the full case list. For pattern analysis, also read reports for cases marked `Resolved` or `Updated`.

If fewer than 3 cases exist:
> "Pattern analysis requires at least 3 cases. You have [N] case(s) so far. Run more consultations to enable pattern analysis."

## 2. Cross-Case Analysis

### Symptom Clustering
- Which symptoms recur across multiple cases?
- Are recurring symptoms potentially linked (e.g., fatigue + joint pain + rash across 3 consultations → consider systemic autoimmune)?

### Diagnostic Trajectory
- Have diagnoses evolved over time? (e.g., "stress headaches" → "migraine" → eventually "elevated BP")
- Are there cases where the initial diagnosis was revised in a second opinion?
- Are there cases marked `Awaiting Tests` with no follow-up?

### Missed or Delayed Diagnoses
- Any conditions that were in the differential but never confirmed or excluded (test never ordered)?
- Cases where confidence was low (<2.5/5) but were never followed up?

### Medication Interactions
- Do any current medications in `_profile.md` correlate with recurring symptoms?
- Example: ACE inhibitor + recurring dry cough → drug side effect, not infection

## 3. Output

```markdown
## ClaudeMed — Pattern Analysis Report
**Generated:** [date]
**Cases analyzed:** [N] (from [earliest date] to [latest date])

---

### Recurring Symptoms
| Symptom | Frequency | Cases | Clinical Pattern |
|---------|-----------|-------|-----------------|
| [symptom] | [N cases] | [#1, #3, #5] | [e.g., consistent with X] |

---

### Diagnostic Consistency
| Diagnosis | Times Reached | Avg Confidence | Confirmed? |
|-----------|--------------|----------------|-----------|
| [Dx] | [N] | [X.X]/5 | [Yes / Pending / No] |

---

### Attention Required

**Unresolved cases (>30 days open):**
[List cases with status Open or Awaiting Tests that are old]

**Low-confidence diagnoses (confidence < 2.5/5):**
[List — these need follow-up or additional testing]

**Potential drug-symptom correlations:**
[Medications from profile vs. recurring symptoms]

---

### Emerging Pattern (if any)
[If recurring symptoms across cases suggest a systemic condition not yet diagnosed — flag it here with rationale and recommended investigation]

---

### Recommended Actions
1. [Specific follow-up for unresolved case]
2. [Suggested additional test for low-confidence case]
3. [Pattern-based recommendation]
```

## 4. Update Tracker

Do not change case statuses automatically. Present recommendations and let the user decide.
