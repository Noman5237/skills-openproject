---
name: log-time
description: Logs time entries against OpenProject work packages. Use this skill whenever the user wants to log hours, record time spent, add a time entry, track time, or book hours on a task. Trigger on phrases like "log 2 hours on #59791", "record time for today", "book 4h on the VAPT task", "I spent 3 hours on testing", "log time for Nazmul on #123", or any request to create time entries. Also triggers when the user says they worked on something and implies hours should be recorded.
---

# Logging Time Entries

## Purpose

Creates time entries against one or more OpenProject work packages. Defaults to today if no date is given. Can log for another user when explicitly requested.

## Workflow

### Step 1: Identify work packages

The user provides work package IDs directly (e.g. `#59791`, `#59488`). If they describe tasks by name instead, use the **search-work-packages** skill to resolve IDs.

### Step 2: Resolve user

- **Default** — log as the authenticated API user. No special handling needed.
- **Other user** — only when the user explicitly names someone (e.g. "log 2h for Nazmul on #59791"). Resolve the name to a numeric ID via `.memory/users/directory.json` or the **find-user** skill.

### Step 3: Resolve date

- No date mentioned → use today's date
- Relative dates ("yesterday", "last Sunday") → resolve to `YYYY-MM-DD`
- Explicit dates ("April 7th", "2026-04-07") → convert to `YYYY-MM-DD`

### Step 4: Collect hours, comment, and activity

- **Hours** (required): parse from user input — "2 hours", "4h", "30 minutes", "1.5h". Convert to ISO 8601 duration (`PT2H`, `PT4H`, `PT30M`, `PT1H30M`).
- **Comment** (optional): include if the user describes what they did.
- **Activity** (optional): if the user specifies an activity type (e.g. "development", "testing", "meeting"), resolve to an activity ID from `.memory/time-entries/activities.json`. If not specified, omit — OpenProject uses the project default.

Activity IDs:

| ID | Name |
|----|------|
| 1 | Management |
| 2 | Specification |
| 3 | Development |
| 4 | Testing |
| 5 | Support |
| 6 | Other |
| 14 | Meeting |
| 15 | Team Support |
| 17 | Design |
| 18 | Documentation |

### Step 5: Preview and confirm

Show a preview table before creating entries:

| WP | Subject | Hours | Date | Comment | Activity |
|----|---------|-------|------|---------|----------|

If logging for another user, include a **User** column.

Ask: "Proceed with logging these time entries?"

### Step 6: Build the input JSON

Write the file at `/tmp/time_entries.json`:

```json
[
  {
    "workPackageId": 59791,
    "hours": "PT2H",
    "spentOn": "2026-04-09",
    "comment": "Fixed XSS vulnerability",
    "activityId": 3,
    "userId": 64
  }
]
```

All fields except `workPackageId`, `hours`, and `spentOn` are optional:
- Omit `userId` to log as the authenticated user
- Omit `activityId` to use the project default
- Omit `comment` if none provided

### Step 7: Log the time entries

```bash
python3 <skill_path>/scripts/log_time.py --input /tmp/time_entries.json
```

### Step 8: Report results

Parse the JSON output and present results using the format in `assets/output-format.md`. Summary:
- **Header**: `Logged N time entries (X.Xh total):`
- **Table**: WP (linked) | Subject | Project | Hours | Date | Comment | Activity
- **User column**: include only if logging for another user
- **Errors** section (if any): list failed entries with error and suggested fix

## Scripts

### `log_time.py`

```bash
python3 <skill_path>/scripts/log_time.py --input <json_file>
```

- Reads the time entries array from `--input`
- POSTs each entry to `/api/v3/time_entries`
- Outputs: `{"logged": [...], "total": N, "totalHours": "X.Xh", "errors": [...]}`

Each entry in `logged` has: `id`, `workPackageId`, `subject`, `project`, `user`, `hours`, `spentOn`, `comment`, `activity`, `link`.

## Memory

- `.memory/users/directory.json` — cached user name → ID mappings
- `.memory/time-entries/activities.json` — activity type ID → name mappings (re-fetch on 422)

## Error Handling

If the script output contains errors, list them after the table:

```
**Failed (M):**
- #WP_ID — <error message>
  Fix: <suggested action>
```

Common causes and fixes:

| Error | Cause | Fix |
|-------|-------|-----|
| 422 Unprocessable | Invalid hours format, missing required field, or invalid activity | Check hours is ISO 8601 (e.g. PT2H), verify activity ID |
| 404 Not Found | WP ID or user ID does not exist | Verify the ID |
| 403 Forbidden | No permission to log time for this user or project | Check permissions |

## Related Skills

- **search-work-packages** — find WP IDs by name or filter (Step 1)
- **find-user** — resolve user name to numeric ID when logging for someone else (Step 2)
- **query-user-costs** — view existing time entries for a user and date range
