# Create Work Packages — Preview Format

Before creating any work packages, show this preview table and ask the user to confirm.

## Table

Present all items depth-first (each parent immediately before its children):

| WBS | Type | Subject | Assignee | Start | Due | Work | Task Type | Status |
|-----|------|---------|----------|-------|-----|------|-----------|--------|
| OPS-11.1 | User story | Auth Epic | Noman | — | — | — | — | New |
| OPS-11.1.1 | Task | Login API | Noman | 2026-04-10 | 2026-04-10 | 8h | API | New |
| OPS-11.1.2 | Task | Write tests | Noman | 2026-04-13 | 2026-04-13 | 4h | Testing | New |

**Columns:**

| Column | Format | Notes |
|--------|--------|-------|
| **WBS** | Text | Computed WBS value (e.g. OPS-11.1.1) |
| **Type** | Text | Work package type (Epic, Feature, User story, Task, …) |
| **Subject** | Text | Title of the item |
| **Assignee** | Text or `—` | Assignee name if provided; `—` if not set |
| **Start** | `YYYY-MM-DD` or `—` | Start date; `—` if not set |
| **Due** | `YYYY-MM-DD` or `—` | Due date; `—` if not set |
| **Work** | `Nh` or `—` | Estimated hours (e.g. `8h`, `4.5h`); `—` if not set |
| **Task Type** | Text or `—` | Value of the Task Type custom field; `—` for non-Task types |
| **Status** | Text | Status name; `New` if not explicitly set |

## Scheduling Note

If dates for a Task were computed by the **assign-work-packages** skill (not explicitly provided),
show the scheduling basis as a sub-row or footnote per task:

```
*(scheduled after "#59488 Dummy Task", due 2026-04-09)*
```

If the assign-work-packages skill returned overload alerts, list them after the table:

```
⚠️  2026-04-10: 12.0h scheduled (Dummy Task, Login API) — exceeds 8h/day
```

Ask the user whether to proceed or adjust dates before confirming.

## Confirmation Prompt

After the table (and any scheduling notes or alerts), ask:

```
Proceed with creating these N work packages?
```

Only write the JSON file and run the create script after the user confirms.
