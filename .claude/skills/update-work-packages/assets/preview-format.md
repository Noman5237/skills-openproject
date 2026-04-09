# Update Work Packages — Preview Format

Before executing any updates, show this preview table and ask the user to confirm.

## Table

| ID | Type | Subject | Changes |
|----|------|---------|---------|
| [#59488](http://project.global.fintech23.xyz/work_packages/59488) | Task | Dummy Task for Testing | assignee → Noman, accountable → Noman, work → 4h, start → 2026-04-09, due → 2026-04-09 |
| [#59487](http://project.global.fintech23.xyz/work_packages/59487) | User story | Dummy User Story for Testing | status → In progress |

**Columns:**

| Column | Format | Notes |
|--------|--------|-------|
| **ID** | `[#ID](link)` | Linked to the current work package |
| **Type** | Text | Current type (e.g. Task, User story) |
| **Subject** | Text | Current subject; show the new value if subject itself is being changed |
| **Changes** | `field → value` | Each change listed as a human-readable label → value pair, comma-separated |

**Change field labels:**

| Input field | Label in Changes |
|-------------|-----------------|
| `assigneeId` | `assignee` → person name |
| `responsibleId` | `accountable` → person name |
| `statusId` | `status` → status name |
| `estimatedHours` | `work` → Nh (e.g. `4h`, `8.5h`) |
| `startDate` | `start` → YYYY-MM-DD |
| `dueDate` | `due` → YYYY-MM-DD |
| `subject` | `subject` → new title |
| `fields.customField1` | `WBS` → value |
| `links.customField3` | `Task Type` → option label |
| `comment` | `comment` → first 60 chars of text + "…" if truncated |
| other custom fields | field label → value |

Always use human-readable names and values in the Changes column — never raw IDs.

## Scheduling Note

If start/due dates were computed by the **assign-work-packages** skill (not provided by the user),
show the scheduling baseline below the table:

```
Scheduled after "#59487 Dummy User Story" (due 2026-04-08) → start 2026-04-09, due 2026-04-09
```

If the assign-work-packages skill returned overload alerts, show them immediately below:

```
⚠️  2026-04-09: 12.0h scheduled (Some Task, new task) — exceeds 8h/day
```

Ask the user whether to proceed or pick a different date.

## Confirmation Prompt

After the table (and any alerts), ask:

```
Proceed with these updates?
```

Only build the input JSON and run the script after the user confirms.
