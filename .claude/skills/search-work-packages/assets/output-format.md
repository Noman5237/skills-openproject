# Search Work Packages — Output Format

## Header

One line summarizing the search:

```
Found N work packages [in "project-name"] [matching: <filter summary>]
```

Filter summary should be human-readable, e.g.:
- `assignee: Noman, status: In progress, On hold`
- `type: Epic, Feature, due before 2026-05-31`
- `subject contains "login", with children`

## Table Structure

Always render the full table — never drop columns for brevity.

Columns: `ID | Type | Subject | Parent | Assignee | Responsible | Status | Start | Due | Work | Spent`

| Column | Format | Notes |
|--------|--------|-------|
| **ID** | `[#ID](link)` | Clickable link to the work package |
| **Type** | Text | e.g. Task, Epic, Feature, User story |
| **Subject** | Text | Full subject title |
| **Parent** | Text | Direct parent title; `-` if none |
| **Assignee** | Text | Name of assignee; `-` if none |
| **Responsible** | Text | Name of responsible/accountable user; `-` if none |
| **Status** | Text | e.g. New, In progress, On hold |
| **Start** | `YYYY-MM-DD` | Start date; `⚠️ -` if missing |
| **Due** | `YYYY-MM-DD` | Due date; `⚠️ -` if missing; `🚨 DATE` if overdue |
| **Work** | `Xh` | Estimated hours (e.g. `8.0h`); `-` if not set |
| **Spent** | `Xh` | Hours logged; `-` if none |

**Column selection:** Show all columns by default. You may omit Responsible if no items have a
responsible user, and omit Parent if no items have a parent — but always keep the core set:
ID, Type, Subject, Assignee, Status, Start, Due, Work, Spent.

## Grouping & Order

1. Group by **project** (one heading per project with item count)
2. Within each project group: show parent items first, then their children indented
3. If `--with-children` was used: indent child rows 2 spaces and prefix subject with `↳`
4. Sort within group by type hierarchy (Epic → Feature → User story → Task) then by ID

## Warnings (⚠️) and Alerts (🚨)

| Condition | Column | Display |
|-----------|--------|---------|
| Start date missing | Start | `⚠️ -` |
| Due date missing | Due | `⚠️ -` |
| Due date is past today (and status not closed) | Due | `🚨 YYYY-MM-DD` |
| Work not estimated | Work | `⚠️ -` |
| Spent > Work (when Work is set) | Spent | `🚨 Xh` |

Rules:
- `🚨` replaces `⚠️` — never show both for the same cell
- Compare due dates against today's date at time of query
- Closed statuses (Closed, Rejected, Dropped, Live) suppress the overdue 🚨
- **On hold** and **New** statuses suppress ⚠️ warnings for missing Due, Work, and Start — these
  items are not yet actively scheduled, so missing fields are expected. Show a plain `-` instead.
  The overdue 🚨 on Due still applies if a due date IS set and is past today.

## Example

Found 5 work packages matching: assignee: Noman, type: Epic, Feature, with children

### Fintech – AI SDKs & PoCs (3 items)

| ID | Type | Subject | Parent | Assignee | Responsible | Status | Start | Due | Work | Spent |
|----|------|---------|--------|----------|-------------|--------|-------|-----|------|-------|
| [#1234](http://project.global.fintech23.xyz/work_packages/1234) | Epic | User Auth System | - | Noman | - | In progress | 2026-04-01 | 2026-05-30 | 80.0h | 20.0h |
| &nbsp;&nbsp;↳ [#1235](http://project.global.fintech23.xyz/work_packages/1235) | Feature | Login with email/password | User Auth System | Noman | - | In progress | 2026-04-01 | 2026-04-30 | 40.0h | 10.0h |
| &nbsp;&nbsp;↳ [#1236](http://project.global.fintech23.xyz/work_packages/1236) | Task | Create login API | Login with email/password | Noman | - | New | - | 🚨 2026-04-08 | 8.0h | - |

### Core Banking Platform (2 items)

| ID | Type | Subject | Parent | Assignee | Responsible | Status | Start | Due | Work | Spent |
|----|------|---------|--------|----------|-------------|--------|-------|-----|------|-------|
| [#2100](http://project.global.fintech23.xyz/work_packages/2100) | Feature | Payment Gateway | - | - | Noman | Scheduled (To Do) | 2026-04-10 | 2026-04-25 | ⚠️ - | - |
| [#2105](http://project.global.fintech23.xyz/work_packages/2105) | Epic | Reporting Module | - | - | Noman | New | - | - | - | - |
