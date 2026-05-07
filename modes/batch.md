# Mode: batch — Parallel Case Processing

**Trigger:** `/claudemed batch`
**Goal:** Process multiple cases in parallel using `claude -p` workers. Each worker handles one case independently with a fresh 200K context.

## Architecture

```
ClaudeMed Conductor (main session)
  │
  │  Reads data/pipeline.md → pending cases
  │
  ├─ Worker 1 (claude -p) → Case A → reports/001-*.md + tracker line
  ├─ Worker 2 (claude -p) → Case B → reports/002-*.md + tracker line
  ├─ Worker 3 (claude -p) → Case C → reports/003-*.md + tracker line
  │
  └─ Merge all tracker lines → data/cases.md + summary
```

## Files

```
batch/
  batch-input.tsv          # Case list (case_id, source, description)
  batch-state.tsv          # Progress (auto-generated)
  batch-prompt.md          # System prompt for workers (injected from _shared.md)
  logs/                    # One log per case (gitignored)
  tracker-additions/       # Tracker lines from workers (gitignored)
```

## Execution

### Step 1 — Read State
Check `batch/batch-state.tsv` → skip already-completed cases.

### Step 2 — Prepare Workers
For each pending case, calculate the next sequential report number.

### Step 3 — Launch Workers

```bash
claude -p --dangerously-skip-permissions \
  --append-system-prompt-file batch/batch-prompt.md \
  "Process this medical case. Case ID: {id}. Description: {text}. Report number: {num}."
```

Each worker is self-contained and produces:
1. Report `.md` in `reports/`
2. Tracker line in `batch/tracker-additions/{id}.tsv`

### Step 4 — Merge Results

After all workers complete:
1. Read all files from `batch/tracker-additions/`
2. Append each line to `data/cases.md`
3. Update `batch/batch-state.tsv` (mark completed)
4. Display summary

## batch-state.tsv Format

```
id	description	status	started_at	completed_at	report_num	confidence	error	retries
1	"Chest pain..."	completed	2026-...	2026-...	002	3.8	-	0
2	"Fatigue..."	failed	2026-...	2026-...	-	-	Error msg	1
3	"Headache..."	pending	-	-	-	-	-	0
```

## Resumability

- If batch dies → re-run → reads `batch-state.tsv` → skip completed
- Lock file (`batch/batch-runner.pid`) prevents double execution
- Worker failure on case #3 doesn't affect cases #1, #2, #4

## Error Handling

| Error | Recovery |
|-------|----------|
| Case file not found | Worker marks `failed`, conductor continues |
| Ambiguous case description | Worker asks for clarification in report, continues |
| URGENT case detected | Worker outputs URGENT flag first, completes report |
| Worker crashes | Conductor marks `failed`, continues. Retry available. |
| Conductor dies | Re-run → reads state → skips completed |
