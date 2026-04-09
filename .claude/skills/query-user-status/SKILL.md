---
name: query-user-status
description: Queries OpenProject work packages by status, type, and assignee. Use when the user asks about tasks, work packages, sprint status, or project progress.
---

# Querying Work Packages

## Purpose

Fetches open work packages assigned to a specific user, grouped by status. Use for sprint reviews, standup prep, or checking what someone is currently working on.

## Workflow

### Step 1: Resolve the user ID

If the user gives a name (not a numeric ID), use the **find-user** skill first to get their numeric user ID.

### Step 2: Run the script

See **Scripts** section below.

### Step 3: Present results to the user

The script returns JSON — do not show raw JSON. Parse and present a formatted table. See `assets/output-format.md` for the full format spec including column definitions, grouping rules, status order, and ⚠️/🚨 warning logic.

## Scripts

```bash
python3 <skill_path>/scripts/query_user_tasks.py <user_id>
python3 <skill_path>/scripts/query_user_tasks.py <user_id> --status 1,7,13
```

- Default statuses: New (1), To Do (6), In progress (7), On hold (13)
- Override with `--status` (comma-separated IDs from `.memory/statuses/list.json`)
- Always run with `--json` flag for machine-readable output before formatting

## Output

See `assets/output-format.md` for the full spec. Summary:
- **Tasks only** — Epics, Features, User Stories, and other non-Task types are filtered out at the API level
- **Grouped by status** (New → Scheduled → In Progress → On Hold), then by project
- **Per task:** ID | Type | Subject | Parent | Start | Due | Work | Spent
- **Flags:** ⚠️ missing start/due; 🚨 overdue, or spent > estimated work
- **Status warning:** Tasks in "New" that already have start + due + work all set show `⚠️ New` in the Status column — these should be moved to "Scheduled (To Do)" or "In Progress" in OpenProject
- **Schedule overload:** checks if the person can finish all tasks by each deadline. For each due date (from today onwards), sums remaining hours of all tasks due on or before that date and compares against total available working hours (weekends and holidays excluded). Flags dates where cumulative work exceeds capacity. Also flags individual tasks that can't be finished in their own available window.

## Notes

Filters are JSON-encoded query params: `?filters=[{"field":{"operator":"op","values":["val"]}}]`
- `"o"` = open (all non-closed statuses); `"="` = equals; `"!"` = not equals
- `assignee` takes a numeric user ID string (e.g. `"64"`)
- `status` and `type` take arrays of ID strings (read from memory files)

## Memory

Before resolving a user name to an ID, check `.memory/users/directory.json`.

For status and type IDs, read from memory instead of hardcoding:
- `.memory/statuses/list.json` — full work package status ID table
- `.memory/types/list.json` — work package type ID table

If these files don't exist yet, use the IDs from common knowledge and write the files after first successful use.

## Related Skills

- **find-user** — resolves assignee name to numeric ID (Step 1)
