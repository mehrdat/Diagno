# Mode: tracker — Case History Overview

Reads and displays `data/cases.md`.

**Tracker format:**
```markdown
| # | Date | Chief Complaint | Specialists Consulted | Top Diagnosis | Confidence | Status | Report | Notes |
```

Possible statuses: `Open` → `Consulted` → `Awaiting Tests` → `Updated` → `Resolved` / `Referred` / `Closed` / `URGENT`

**Display the tracker with statistics:**

```
ClaudeMed — Case Tracker
========================

Total cases: [N]
By status:
  Consulted:       [N]
  Awaiting Tests:  [N]
  Updated:         [N]
  Resolved:        [N]
  Referred:        [N]
  Open:            [N]
  URGENT:          [N]  ← highlight in red if > 0

Average diagnostic confidence: [X.X]/5
Most common chief complaints: [list top 3]
Active specialists consulted: [list]

Open / Awaiting Tests (needs attention):
[Table of cases with status = Open or Awaiting Tests]

Recent cases (last 5):
[Table]
```

If the user asks to update a case status, edit the corresponding row in `data/cases.md`.

If the user asks to see a specific report, read the file from `reports/` and display it.

If `data/cases.md` is empty or does not exist, say:
> "No cases tracked yet. Run `/claudemed {symptoms}` to start your first consultation."
