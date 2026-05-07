# Mode: differential — Ranked Differential Diagnosis

**Trigger:** `/claudemed differential`
**Goal:** Generate or update a comprehensive ranked differential diagnosis from all available case data without re-running the full debate. Useful when new information arrives (new labs, imaging, exam findings) and the user wants an updated differential without a full consultation.

## 1. Gather All Available Data

Pull from:
1. Latest report in `reports/` (if it exists)
2. `data/intake/` (any new files since last report)
3. User's current message (new findings, test results, symptom changes)
4. `modes/_profile.md` and `config/patient.yml`

## 2. Safety Triage

Check for red flags. Issue URGENT warning if present.

## 3. Data Delta (if updating)

If a prior case exists, note:
- What data is NEW since the last consultation
- How the new data shifts the probabilities (Bayesian update)
- Which diagnoses are strengthened / weakened / eliminated

## 4. Generate Differential

Produce a comprehensive ranked differential:

```markdown
## Ranked Differential Diagnosis
**Updated:** [YYYY-MM-DD]
**Case:** [###] — [Chief Complaint]
**New data incorporated:** [List what's new, or "Initial" if first run]

---

### Category A — Most Likely (Confidence ≥ 3.5/5)

**1. [Diagnosis]** | ICD-10: [code] | Confidence: [X.X]/5
- **For:** [evidence supporting]
- **Against:** [what doesn't fit]
- **Confirming test:** [single best test to confirm this]
- **Excluding test:** [single best test to exclude this if not confirmed]

**2. [Diagnosis]** | ICD-10: [code] | Confidence: [X.X]/5
[same structure]

---

### Category B — Possible (Confidence 2.0–3.4/5)

**3. [Diagnosis]** | ICD-10: [code] | Confidence: [X.X]/5
[structure]

**4. [Diagnosis]** | ICD-10: [code] | Confidence: [X.X]/5
[structure]

---

### Category C — Less Likely but Clinically Important (Cannot Miss)
These may have lower pre-test probability but have serious consequences if missed:

**[Diagnosis]** | ICD-10: [code]
- **Why it must be excluded:** [consequence of missing]
- **Excluding test:** [test to rule out]
- **Current evidence against:** [why probability is lower]

---

### Effectively Excluded
- **[Diagnosis]:** [Reason — finding X rules this out]
- **[Diagnosis]:** [Reason]

---

## Information Still Needed

| Missing Data | Would Help Diagnose | Would Help Exclude |
|--------------|--------------------|--------------------|
| [Test/finding] | [Diagnosis] | [Diagnosis] |
| [Test/finding] | [Diagnosis] | [Diagnosis] |

---

## Probability Shifts (if updating prior differential)

| Diagnosis | Previous Confidence | Updated Confidence | Reason |
|-----------|--------------------|--------------------|--------|
| [Dx] | [X.X]/5 | [X.X]/5 | [new data] |
```

## 5. Update Tracker

If this updates an existing case, change its status to `Updated` in `data/cases.md`.
