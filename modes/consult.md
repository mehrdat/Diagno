# Mode: consult — Full Consultation Pipeline (Auto-Pipeline)

When the user describes symptoms, pastes a case, or provides a file path without an explicit sub-command, run the ENTIRE consultation pipeline in sequence.

## Step 0 — Input Processing

**If the input is a file path** (e.g., `data/intake/symptoms-2026-05-04.md`):
- Read the file directly
- Use its contents as the case presentation

**If the input is raw text:**
- Use directly as the chief complaint and case presentation

**If the input contains a URL** (e.g., lab results online, imaging report):
1. **WebFetch** to retrieve content
2. **WebSearch** as fallback if fetch fails
3. If nothing works: ask user to paste the content directly

**Check for intake files:**
Before starting, check if `data/intake/` has any relevant files (symptom logs, lab results, imaging reports). If found, incorporate them silently.

---

## Step 1 — Safety Triage (MANDATORY — DO NOT SKIP)

Before any analysis, check the presenting symptoms against the red-flag list in `modes/_shared.md`.

**If ANY red flag is present:**
- Output the `⚠️ URGENT` block immediately
- Continue with analysis, clearly marked "for reference only"

**If no red flags:**
- Continue to Step 2

---

## Step 2 — Case Formulation

Structure the presenting case into a formal clinical summary:

```
**Chief Complaint:** [Primary symptom(s) in patient's words]
**HPI (History of Present Illness):**
  - Onset: [When did it start?]
  - Location: [Where exactly?]
  - Duration: [How long per episode?]
  - Character: [Describe quality: sharp, dull, throbbing, burning...]
  - Associated symptoms: [What else is present?]
  - Relieving factors: [What makes it better?]
  - Aggravating factors: [What makes it worse?]
  - Severity: [1–10 scale if applicable]
  - Timing: [Constant / intermittent / progressive?]
  
**Relevant PMH from profile:** [Pull from _profile.md — age, conditions, meds, allergies]
**Relevant family history:** [From _profile.md]
**Current medications:** [From _profile.md — note interactions with symptoms]
**Vital signs (if provided):** [BP, HR, Temp, SpO2, RR, Weight change]
**Objective findings (if provided):** [Labs, imaging, physical exam findings]
```

If critical information is missing, note it as `[Not provided — ask]`.

---

## Step 3 — Specialist Debate

Determine which specialists from the panel in `_shared.md` are relevant to this case.
**Activate only relevant specialists.** Do not include irrelevant ones.

Run all 4 debate rounds as defined in `modes/_shared.md`:

### Round 1 — Initial Presentations
Each activated specialist presents their primary hypothesis with supporting evidence from the case.

### Round 2 — Cross-Examination  
Each specialist challenges the others. Identify the strongest conflicts.

### Round 3 — Evidence Integration
Dr. Internal Medicine synthesizes all arguments. Updates probability weights. Lists missing data that would change the ranking.

### Round 4 — Consensus Ranking
Produce the final ranked differential:

```
## Differential Diagnosis

| Rank | Diagnosis | ICD-10 | Confidence | Key Evidence For | Key Evidence Against |
|------|-----------|--------|------------|-----------------|---------------------|
| 1 | [Most likely] | [code] | [score]/5 | [why] | [what argues against] |
| 2 | [Second] | [code] | [score]/5 | [why] | [what argues against] |
| 3 | [Third] | [code] | [score]/5 | [why] | [what argues against] |
...
| — | [Rule out] | [code] | — | — | [why excluded] |
```

---

## Step 4 — Literature Search

For the top 1–2 diagnoses on the differential, search current medical literature:

1. **WebSearch** using: `site:pubmed.ncbi.nlm.nih.gov [condition] [key finding] guidelines 2023 OR 2024 OR 2025`
2. **WebSearch** for relevant clinical guidelines: `[condition] clinical guidelines [specialty society] 2024`
3. Note any recent developments (new diagnostic criteria, updated treatment guidelines, emerging evidence)

Incorporate findings into the report. Note evidence quality and year.

---

## Step 5 — Workup Recommendations

Provide a prioritized list of recommended next steps:

```
## Recommended Workup

### Immediate (Order Now)
- [Test name]: to [confirm/exclude] [diagnosis]. Expected turnaround: [time].

### Short-term (Within 1–2 Weeks)  
- [Test name]: to [purpose].

### Specialist Referral
- [Specialty]: for [reason]. Urgency: [routine / soon / urgent].

### Watchful Waiting (if appropriate)
- [Symptom to monitor] — return if [threshold].
```

---

## Step 6 — Save Report

Save to `reports/{###}-{chief-complaint-slug}-{YYYY-MM-DD}.md`.

Use this exact format:

```markdown
# [Chief Complaint] — Consultation Report
**Date:** [YYYY-MM-DD]
**Case #:** [###]
**Patient:** [Age/Sex from profile, no identifying info]
**Consulting Specialists:** [List activated specialists]

---

## Case Summary
[Structured clinical summary from Step 2]

---

## Specialist Debate Summary

### Round 1 — Initial Presentations
[...]

### Round 2 — Cross-Examination
[...]

### Round 3 — Synthesis
[...]

---

## Differential Diagnosis
[Table from Step 3]

**Overall Diagnostic Confidence: [X.X]/5**

---

## Supporting Evidence
[Literature findings from Step 4, with sources and dates]

---

## Recommended Workup
[Ordered list from Step 5]

---

## Questions to Ask Your Doctor
[5–8 specific, informed questions the patient should ask their physician — based on the differentials]

---

## Red Flags to Watch For
[Symptoms that would warrant immediate emergency care, specific to this case]

---

*Generated by ClaudeMed. This report is a clinical thinking aid — not a diagnosis. Consult a qualified physician for diagnosis and treatment.*
```

---

## Step 7 — Update Case Tracker

Append to `data/cases.md`:

```
| {###} | {date} | {chief-complaint} | {specialists} | {top-diagnosis} | {confidence}/5 | Consulted | [Report](reports/{filename}) | {key notes} |
```

**If any step fails**, continue with remaining steps and note the failure in the report.
