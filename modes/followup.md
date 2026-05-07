# Mode: followup — Pending Follow-Ups and Open Cases

**Trigger:** `/claudemed followup`
**Goal:** Surface all cases that need attention — awaiting test results, unresolved diagnoses, scheduled re-evaluations.

## 1. Load Open Cases

Read `data/cases.md`. Filter for:
- Status = `Open`
- Status = `Awaiting Tests`
- Status = `URGENT` (if any remain unresolved)

Also check if any `Consulted` cases have notes indicating follow-up dates.

## 2. Display Follow-Up Dashboard

```
ClaudeMed — Follow-Up Dashboard
================================
Date: [today]

⚠️  URGENT (needs immediate attention): [N]
[Table of URGENT cases]

🔬 Awaiting Test Results: [N]
[Table with: case#, date ordered, test name, what it would confirm/exclude]

📋 Open / Unresolved: [N]
[Table with: case#, date opened, chief complaint, last action, days open]

📅 Scheduled Re-Evaluations: [N]
[Cases where the report recommended "return in X weeks if Y persists"]
```

## 3. Prompt for Each Open Case

For each open case, offer:
> - "Enter new test results for Case #[N]"
> - "Mark as Resolved"
> - "Run second opinion"
> - "Search literature on [top diagnosis]"
> - "No update needed, skip"

## 4. New Data Entry

If the user provides test results or new findings:
1. Append the new data to `data/intake/` as `{case_id}-followup-{date}.md`
2. Run `modes/differential.md` to update the differential with new data
3. Update case status to `Updated` in `data/cases.md`

## 5. Closing Cases

If the user marks a case as `Resolved`:
- Ask: "What was the confirmed diagnosis?"
- Update the case row in `data/cases.md` with confirmed diagnosis
- Change status to `Resolved`
- Note: this feedback improves pattern analysis accuracy
