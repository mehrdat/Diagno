# Mode: literature — Medical Literature Search

**Trigger:** `/claudemed literature {query}`
**Goal:** Search current medical literature for a condition, symptom cluster, treatment, or clinical question. Return evidence-graded summaries with source quality ratings.

## 1. Parse the Query

The query may be:
- A condition: "lupus" → search for current diagnostic criteria, epidemiology, treatment
- A clinical question: "what is the sensitivity of D-dimer for PE" → targeted evidence search
- A symptom + condition: "fatigue in hypothyroidism" → mechanism + diagnostic approach
- A treatment: "metformin in non-diabetic PCOS" → evidence for off-label use

## 2. Evidence Search Strategy

### Tier 1 — Systematic Reviews & Guidelines (search first)
```
WebSearch: site:pubmed.ncbi.nlm.nih.gov "{condition}" systematic review 2022 OR 2023 OR 2024 OR 2025
WebSearch: "{condition}" clinical practice guidelines {specialty society} 2023 OR 2024
```

Specialty societies to check by domain:
- Cardiology: AHA, ACC, ESC
- Neurology: AAN
- Rheumatology: ACR, EULAR
- GI: ACG, BSG
- Pulmonology: ATS, ERS
- Endocrinology: ADA, AACE, Endocrine Society
- Infectious Disease: IDSA, WHO
- Oncology: NCCN, ESMO
- General: USPSTF (screening), Cochrane (meta-analyses), UpToDate, BMJ Best Practice

### Tier 2 — Key Clinical Trials
```
WebSearch: site:pubmed.ncbi.nlm.nih.gov "{condition}" randomized controlled trial 2020 OR 2021 OR 2022 OR 2023 OR 2024
```

### Tier 3 — Emerging Evidence
```
WebSearch: "{condition}" new research 2025 site:nejm.org OR site:thelancet.com OR site:bmj.com
```

## 3. Evidence Summary Format

For each source found:

```markdown
### [Finding / Guideline Title]
**Source:** [Journal/Organization] | **Year:** [YYYY] | **Evidence Level:** [Ia / Ib / IIa / IIb / III / IV]
**URL:** [if available]

**Key finding:** [1–3 sentences on the core clinical message]
**Clinical implication:** [What this means for diagnosis or treatment]
**Limitations:** [Sample size, population, conflict of interest, etc.]
```

**Evidence Level Key:**
| Level | Definition |
|-------|-----------|
| Ia | Systematic review of RCTs |
| Ib | Single RCT |
| IIa | Controlled study without randomization |
| IIb | Quasi-experimental study |
| III | Descriptive / observational studies |
| IV | Expert opinion, case reports, consensus |

## 4. Clinical Summary

After searching, synthesize:

```markdown
## Evidence Summary: [Query]
**Search date:** [YYYY-MM-DD]
**Sources reviewed:** [N]

### Current Consensus
[What the weight of evidence says about this condition/question]

### Diagnostic Criteria (if applicable)
[Current validated criteria — ICD-10, DSM-5, ACR, etc.]

### Treatment Evidence
[First-line, second-line, and emerging treatments with evidence grades]

### Controversies / Emerging Research
[Areas where evidence is incomplete, conflicting, or rapidly evolving]

### Bottom Line for This Case
[How this literature applies specifically to the current patient case, if there is one]
```

## 5. Gaps

Flag explicitly:
- Areas where evidence is weak (mainly case reports / Level IV)
- Conditions that are underdiagnosed or underresearched in specific populations
- Recent (2024–2025) changes to guidelines that practitioners may not yet have adopted
