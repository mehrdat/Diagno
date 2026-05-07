# Mode: specialist — Single Specialist Consultation

**Trigger:** User invokes `/claudemed specialist {name}` (e.g., `/claudemed specialist cardiology`).
**Goal:** Get an in-depth opinion from one specific specialist, with full depth of that domain.

## 1. Identify Specialist

Match the requested specialty from the panel in `_shared.md`. Accept common abbreviations and aliases:
- cardio / cardiology / cardiologist → **Dr. Cardiology**
- neuro / neurology / neurologist → **Dr. Neurology**
- rheum / rheumatology / rheumatologist → **Dr. Rheumatology**
- gi / gastro / gastroenterology → **Dr. Gastroenterology**
- pulm / pulmonology / pulmonologist → **Dr. Pulmonology**
- endo / endocrinology / endocrinologist → **Dr. Endocrinology**
- id / infectious disease / infectious → **Dr. Infectious Disease**
- heme / hematology / hematologist → **Dr. Hematology**
- derm / dermatology / dermatologist → **Dr. Dermatology**
- psych / psychiatry / psychiatrist → **Dr. Psychiatry**
- onco / oncology / oncologist → **Dr. Oncology**
- nephro / nephrology / nephrologist → **Dr. Nephrology**
- uro / urology / urologist → **Dr. Urology**
- im / internal medicine / internist → **Dr. Internal Medicine**

If the specialty cannot be matched, list available specialists and ask the user to clarify.

## 2. Safety Triage

Check for red flags. Issue URGENT warning if present.

## 3. Deep Specialist Assessment

The identified specialist provides a detailed domain-specific evaluation:

```
## Consultation: Dr. [Specialty]

### Specialty Assessment
[Detailed evaluation from this specialist's perspective, going deeper than the standard debate format would allow]

### Domain-Specific History Points
What additional history is critical from this specialist's viewpoint:
- [Question 1]
- [Question 2]
- [Question 3]

### Physical Exam Findings to Seek
- [Exam finding 1]: suggests [diagnosis]
- [Exam finding 2]: would confirm/exclude [diagnosis]

### Recommended Investigations (Domain-Specific)
| Test | Purpose | Sensitivity | Specificity | When to Order |
|------|---------|-------------|-------------|---------------|
| [Test] | [what it answers] | [%] | [%] | [now/if X/routine] |

### Differential (from this specialty's lens)
| Diagnosis | ICD-10 | Confidence | Key Criteria |
|-----------|--------|------------|-------------|
| [Dx 1] | [code] | [X.X]/5 | [criteria] |
| [Dx 2] | [code] | [X.X]/5 | [criteria] |

### Treatment Considerations (if diagnosis confirmed)
[First-line treatments, contraindications given patient medications/conditions, monitoring requirements]

### When to Refer
[Criteria that would prompt referral to this specialty, or escalation within it]

### Specialist's Literature Note
[1–2 key references, guidelines, or recent findings from this domain relevant to the case]
```

## 4. Caveats

Note explicitly which aspects of the case fall OUTSIDE this specialist's domain and should be cross-checked with other specialties.

## 5. Save to Report

If a report already exists for this case, append this specialist's section to it. Otherwise create a new report: `reports/{###}-specialist-{specialty}-{date}.md`.
