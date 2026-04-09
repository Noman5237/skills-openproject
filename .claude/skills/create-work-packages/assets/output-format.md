# Create Work Packages — Output Format

## Header

One line summarizing the result:

```
Created N work packages in "project-name":
```

If there were errors, append a second line:

```
Created N work packages in "project-name" (M failed):
```

## Table

Present all successfully created work packages in a flat table, parents before children.

| Column | Format | Notes |
|--------|--------|-------|
| **ID** | `[#ID](link)` | Clickable link to the work package |
| **Type** | Text | e.g. Epic, Feature, User story, Task |
| **Subject** | Text | Full subject title |
| **Assignee** | Text or `—` | Assignee name; `—` if not set |
| **Start** | `YYYY-MM-DD` or `—` | Start date; `—` if not set |
| **Due** | `YYYY-MM-DD` or `—` | Due date; `—` if not set |
| **Work** | `Nh` or `—` | Estimated hours (e.g. `8h`, `4.5h`); `—` if not set |
| **Status** | Text | Status assigned (e.g. New, In progress) |

Ordering: depth-first — each parent row is immediately followed by its children, then
grandchildren, before the next sibling. Indent child subjects with `↳ ` to show hierarchy.

## Example

Created 3 work packages in "Devops Support":

| ID | Type | Subject | Assignee | Start | Due | Work | Status |
|----|------|---------|----------|-------|-----|------|--------|
| [#1234](http://project.global.fintech23.xyz/work_packages/1234) | User story | Auth User Story | Noman | — | — | — | New |
| [#1235](http://project.global.fintech23.xyz/work_packages/1235) | Task | ↳ Login API endpoint | Noman | 2026-04-10 | 2026-04-10 | 8h | New |
| [#1236](http://project.global.fintech23.xyz/work_packages/1236) | Task | ↳ Write unit tests | Noman | 2026-04-13 | 2026-04-13 | 4h | New |
