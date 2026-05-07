# Mode: pipeline — Process Pending Cases

**Trigger:** `/claudemed pipeline`
**Goal:** Process all pending cases from `data/pipeline.md` in sequence.

## 1. Read Pipeline

Read `data/pipeline.md`. Identify all entries with status `Pending`.

If pipeline is empty:
> "No pending cases in the pipeline. Add symptom descriptions or file paths to `data/pipeline.md` under the Pending section."

## 2. Process Each Case

For each pending entry:

1. Extract the case text or file path
2. Run the full `consult` pipeline (read `modes/consult.md`)
3. Mark as `Processed` in `data/pipeline.md` with the report filename
4. Continue to the next case

## 3. Pipeline File Format

`data/pipeline.md` uses this structure:

```markdown
# Case Pipeline

## Pending
<!-- Add new cases here. One per entry. -->

### Case: [brief description]
**Added:** [date]
**Source:** [patient input / file / other]
[Symptom description or file path to data/intake/]

---

### Case: [brief description]
[...]

## Processed
<!-- Auto-moved here after consultation -->

| Date Processed | Case | Report | Status |
|----------------|------|--------|--------|
```

## 4. Batch Handling

If there are 3+ pending cases, offer to run as batch:
> "Found [N] pending cases. Run as batch for parallel processing? (`/claudemed batch`) or process sequentially?"

If the user confirms sequential, process one by one.
