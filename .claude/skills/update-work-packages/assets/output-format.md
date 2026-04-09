# Update Work Packages — Output Format

## Header

```
Updated N work packages:
```

If there were errors:

```
Updated N work packages (M failed):
```

## Table

Flat table of all successfully updated work packages, showing the new values of key fields
after the update alongside which fields were changed.

| Column | Format | Notes |
|--------|--------|-------|
| **ID** | `[#ID](link)` | Clickable link to the work package |
| **Type** | Text | e.g. Task, User story, Epic |
| **Subject** | Text | Current subject (new value if subject was changed) |
| **Assignee** | Text or `—` | Assignee after update; `—` if unset |
| **Start** | `YYYY-MM-DD` or `—` | Start date after update; `—` if unset |
| **Due** | `YYYY-MM-DD` or `—` | Due date after update; `—` if unset |
| **Work** | `Nh` or `—` | Estimated hours after update (e.g. `4h`, `8.5h`); `—` if unset |
| **Status** | Text | Status after update |
| **Changed** | Text | Comma-separated list of updated fields |

## Example

Updated 2 work packages:

| ID | Type | Subject | Assignee | Start | Due | Work | Status | Changed |
|----|------|---------|----------|-------|-----|------|--------|---------|
| [#59487](http://project.global.fintech23.xyz/work_packages/59487) | User story | Dummy User Story for Testing | Noman | 2026-04-09 | — | — | New | assignee, responsible |
| [#59488](http://project.global.fintech23.xyz/work_packages/59488) | Task | Dummy Task for Testing | Noman | 2026-04-09 | 2026-04-09 | 4h | New | assignee, responsible, startDate, work |
