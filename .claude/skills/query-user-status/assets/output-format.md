# Work Packages Output Format

## Table Structure

Columns: `ID | Type | Subject | Parent | Start | Due | Work | Spent`

- **ID**: clickable link → `[ID](http://project.global.fintech23.xyz/work_packages/ID)`
- **Parent**: direct parent title; `-` if none
- **Work / Spent**: decimal hours (e.g. `4.0h`); `-` if null or zero

## Grouping & Order

1. Group by **status** (heading), then by **project** (bold subheading with task count)
2. Status order: **New** → **Scheduled (To Do)** → **In Progress** → **On Hold**
3. Only include a project subheading under a status if it has tasks in that status
4. Summary line at top: e.g. `**27 open tasks** for <name> across 3 projects`

## Warnings (⚠️) and Alerts (🚨)

| Condition | Column | Display |
|-----------|--------|---------|
| Start date missing | Start | `⚠️ -` |
| Due date missing | Due | `⚠️ -` |
| Due date is past today | Due | `🚨 YYYY-MM-DD` |
| Work not estimated | Work | `⚠️ -` |
| Spent > Work | Spent | `🚨 Xh` |
| Task is "New" but has start + due + work all set (`scheduledInNew: true`) | Status | `⚠️ New` |

Rules:
- 🚨 replaces ⚠️ — never show both for the same cell
- Compare due dates against today's date at time of query
- **On hold** and **New** statuses suppress ⚠️ warnings for missing Due, Work, and Start — these
  items are not yet actively scheduled, so missing fields are expected. Show a plain `-` instead.
  The overdue 🚨 on Due still applies if a due date IS set and is past today.

## Schedule Overload

After the task table, if the JSON output contains `overloaded_dates` entries, show them as a separate section. Each entry represents a deadline by which cumulative remaining work exceeds available working hours.

The check is cumulative: tasks are sorted by due date, and remaining hours are summed progressively. At each due date, if the total remaining work across all tasks due by then exceeds the total working hours available from today to that date (weekends and holidays excluded), that date is flagged.

**Header per overloaded date:**
```
🚨 By 2026-04-13 — 20.0h remaining, 16.0h available (4.0h over capacity)
```

**Table columns:**

| Column | Format | Notes |
|--------|--------|-------|
| **ID** | `[#ID](link)` | Clickable link |
| **Type** | Text | e.g. Task |
| **Subject** | Text | Task title |
| **Parent** | Text or `-` | Direct parent |
| **Status** | Text | Current status |
| **Start** | `YYYY-MM-DD` | Effective start: today if startDate is missing or past; actual startDate if future |
| **Due** | `YYYY-MM-DD` | Due date |
| **Work** | `Nh` or `—` | Estimated hours |
| **Spent** | `Nh` or `—` | Hours logged |
| **Remaining** | `Nh` | Remaining hours; prefix with `🚨` if this single task alone can't fit in its available window (`feasible: false`) |

The table includes ALL tasks due on or before the flagged date — not just tasks due on that exact date — so the full competing workload is visible.

Only dates from today onwards are shown. Past overloaded dates are omitted.

```
### ⚠️ Schedule Overload

🚨 By 2026-04-09 — 12.0h remaining, 8.0h available (4.0h over capacity)

| ID | Type | Subject | Parent | Status | Start | Due | Work | Spent | Remaining |
|----|------|---------|--------|--------|-------|-----|------|-------|-----------|
| [59488](...) | Task | Login API | Auth Feature | On hold | 2026-04-09 | 2026-04-09 | 8.0h | 2.0h | 6.0h |
| [59491](...) | Task | Write tests | Auth Feature | In progress | 2026-04-09 | 2026-04-09 | 4.0h | - | 🚨 4.0h |
```

## Example

**27 open tasks** for Md. Abdullah Al Noman across 3 projects

### In Progress (8 tasks)

**Fintech- AI SDKs & PoCs** (5 tasks)

| ID | Type | Subject | Parent | Start | Due | Work | Spent |
|----|------|---------|--------|-------|-----|------|-------|
| [57943](http://project.global.fintech23.xyz/work_packages/57943) | Task | Market Research | Market Research, PRD & System Design | 2026-03-15 | 2026-04-09 | 4.0h | - |
| [57944](http://project.global.fintech23.xyz/work_packages/57944) | Task | API Integration | Market Research, PRD & System Design | ⚠️ - | 🚨 2026-03-01 | ⚠️ - | 🚨 6.0h |
