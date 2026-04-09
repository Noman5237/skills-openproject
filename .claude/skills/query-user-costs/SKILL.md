---
name: query-user-costs
description: Shows time entries spent per user for a date range, grouped by project. Use when the user asks about hours logged, time spent, billable hours, cost reports, or wants to see what someone worked on over a period.
---

# Querying Cost Reports

## Purpose

Shows all time entries logged by a specific user over a date range, grouped by project. Use for sprint retrospectives, billing reviews, or checking if someone is over/under capacity.

## Workflow

### Step 0: Resolve the date range

Always exclude today — the current day's logs are incomplete.

**"Last X working days"** — use the workdays skill:
```bash
WORKDAYS=<workdays_skill_path>/scripts/dates.py
python3 $WORKDAYS cache-status <YEAR>   # ensure cache is fresh first
python3 $WORKDAYS prev <today> X        # → start_date
python3 $WORKDAYS prev <today> 1        # → end_date
```
Example: today = 2026-04-08 (Wed), "last 3 working days" → start = 2026-04-05, end = 2026-04-07

**"Last X days"** (calendar): end = yesterday, start = today minus X days

**Explicit range given:** use as-is, clip end to yesterday if today is included.

### Step 1: Resolve user ID

If the user gives a name, use the **find-user** skill to get the numeric user ID.

### Step 2: Run the script

See **Scripts** section below.

### Step 3: Present results

Parse the JSON output and format as described in `assets/output-format.md` — grouped by project, with ⚠️ on task statuses that are New or To Do (time logged before work started).

## Scripts

```bash
python3 <skill_path>/scripts/query_time_entries.py <user_id> <start_date> <end_date>
```

- `user_id`: numeric ID (use find-user skill to resolve a name)
- Dates in `YYYY-MM-DD` format
- Output: JSON with `entries`, `totals`, and `user` fields

## Output

See `assets/output-format.md` for the full spec. Summary:
- **Header:** `X time entries for <name>, <start> → <end> — Y.Yh total`
- **Grouped by project** with subtotals
- **Per entry:** Date | Task | Status | Start | Due | Work | Spent | Hours | Comment
- **Flags:** 🚨 for 0h days, <6h days (>0), or >10h days; 🚨 on Due for tasks closed after due date

## Notes

- Time entries use `<>d` operator for date range (same start/end for a single day)
- URL filter params require compact JSON — use `separators=(',', ':')` in `json.dumps`
- `sortBy=["project","asc"]` is not supported; sort by `spentOn` only
- Work package status is not in time entry responses — batch-fetch via `/api/v3/work_packages?filters=[{"id":{"operator":"=","values":[...]}}]`

## Memory

Before resolving a user name to an ID, check `.memory/users/directory.json`. If the name matches a cached entry, use that ID without an API call.

## Related Skills

- **find-user** — resolves user name to numeric ID (Step 1)
- **workdays** — resolves "last X working days" to exact date range (Step 0)
