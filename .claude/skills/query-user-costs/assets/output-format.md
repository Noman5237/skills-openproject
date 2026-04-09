# Time Entries Output Format

## Summary line
`**X time entries** for <name>, <start> → <end> — **Y.Yh total**`

## Grouping
Group entries by **project**. For each project show a heading with its subtotal:
`### <Project Name> (X.Xh, N entries)`

Then a table:

| Date | Task | Status | Start | Due | Work | Spent | Hours | Comment |
|------|------|--------|-------|-----|------|-------|-------|---------|

- **Status**: shown as-is; prefix ⚠️ if `New`, `Scheduled (To Do)`, or `To be scheduled`
- **Start / Due**: WP start and due dates; `-` if not set
- **Work**: WP estimated time in decimal hours (e.g. `4.0h`); `-` if not set (0)
- **Spent**: WP total spent (across all time, not just this date range)
- **Hours**: hours logged in this specific time entry
- **Comment**: entry comment; `-` if empty

## Alerts (🚨)

| Condition | Column | Display |
|-----------|--------|---------|
| Status is Closed AND `updatedAt` > `dueDate` (closed after due date) | Due | `🚨 YYYY-MM-DD` |
| `totalSpent` > `work` (only when work > 0) | Spent | `🚨 X.Xh` |

Rules:
- 🚨 on Due only applies to Closed tasks where a due date exists and updatedAt is later than the due date
- 🚨 on Spent only fires when a work estimate exists — no estimate means nothing to compare against
- `updatedAt` is used as a proxy for when the task was last transitioned (i.e. closed)

## Daily Summary
Before the per-project footer, show a daily breakdown of total hours logged across all projects. Include **every calendar day in the queried date range** — not just days with entries. Sum `hours` by `date` for days that have entries; show `0.0h` for days with no entries.

Flags (inline in the Total Hours cell):
- 🚨 if total = 0h — no log at all
- 🚨 if total < 6h (but > 0h) — short workday
- *(no flag)* if total is 6h–10h — normal
- 🚨 if total > 10h — excessive hours

| Date | Total Hours |
|------|-------------|
| 2026-04-06 | 8.0h |
| 2026-04-07 | 🚨 3.5h |
| 2026-04-08 | 🚨 0.0h |
| 2026-04-09 | 🚨 11.0h |

## Footer
End with a per-project subtotal table:

| Project | Hours | Entries |
|---------|-------|---------|
| Project A | 4.0h | 2 |
| **Total** | **6.0h** | **3** |

## Example

**3 time entries** for Md. Abdullah Al Noman, 2026-03-24 → 2026-04-06 — **6.25h total**

### City Remit AMC (0.25h, 1 entry)

| Date | Task | Status | Start | Due | Work | Spent | Hours | Comment |
|------|------|--------|-------|-----|------|-------|-------|---------|
| 2026-03-24 | Expired Passport Validation | Closed | 2026-02-01 | 🚨 2026-03-20 | 2.0h | 🚨 3.5h | 0.25h | - |

### Zoober Pay Development (4.0h, 1 entry)

| Date | Task | Status | Start | Due | Work | Spent | Hours | Comment |
|------|------|--------|-------|-----|------|-------|-------|---------|
| 2026-03-24 | AWS UAT Estimation | ⚠️ New | 2026-03-01 | 2026-04-30 | - | 4.0h | 4.0h | - |
