---
name: search-work-packages
description: Searches OpenProject work packages with flexible, composable filters — by subject/name, ID, assignee, accountable (responsible), status, type, project, start/due date ranges, and project-specific custom fields. Filters can be combined freely. Optionally expands matched items to show their direct children (1 level). Use this skill whenever the user wants to find, look up, filter, or list work packages by any attribute — e.g. "find all open bugs assigned to X", "show epics due this month", "list tasks with WBS 1.2", "search for work packages by name", "what tasks are overdue in project Y", "show me everything Noman is responsible for", "get children of these work packages".
---

# Searching Work Packages

## Purpose

Finds work packages across projects using any combination of filters: subject text, IDs, assignee, accountable user, status, type, date ranges, and custom fields. More flexible than `query-user-status` (which is focused on one user's open tasks) — use this when you need to search by arbitrary criteria or across multiple dimensions at once. The `--with-children` flag adds direct child items under each match (1 level only), useful for reviewing an epic's features or a feature's tasks.

## Workflow

### Step 1: Resolve user names to IDs

If the user mentions a person's name for assignee or responsible/accountable:
- Check `.memory/users/directory.json` first — if the name matches a cached entry, use that ID
- Otherwise use the **find-user** skill to look up the numeric user ID

### Step 2: Map status and type names to IDs

Translate any human-readable names to numeric IDs before calling the script:
- Status names → IDs: read `.memory/statuses/list.json` (e.g. "In Progress" → 7, "New" → 1)
- Type names → IDs: read `.memory/types/list.json` (e.g. "Epic" → 5, "Task" → 1, "Feature" → 4)

### Step 3: Handle custom field filters

If the user wants to filter by a custom field (e.g. "Task Type = API", "WBS starts with 1.2"), look up the `fieldKey` and option IDs from two sources — merge both:

1. **Global fields** — read `.memory/custom-fields/global.json` (WBS, Task ID, Task Type, Earned Story Points; no staleness check)
2. **Project-specific fields** — check `.memory/projects/{slug}/custom-fields.json`:
   - If it exists and `meta.lastUpdated` is within 90 days, use it
   - If missing or stale, fetch the schema: `python3 <project_root>/.claude/scripts/fetch_schema.py <project_id> <type_id>`, exclude any `fieldKey` already in `global.json`, and save the remainder

Use `--custom-text fieldKey=value` for text fields (substring match) or `--custom-option fieldKey=optionId` for list-type fields

### Step 4: Run the script

Build the CLI invocation from the resolved filters and run the script. All filter flags are optional and combine as AND logic.

```bash
python3 <skill_path>/scripts/search_work_packages.py \
  [--project PROJECT_ID] \
  [--subject "search text"] \
  [--id 123,456] \
  [--assignee USER_ID] \
  [--responsible USER_ID] \
  [--status 1,7,13 | --status-open] \
  [--type 1,4,5] \
  [--start-from YYYY-MM-DD] [--start-to YYYY-MM-DD] \
  [--due-from YYYY-MM-DD] [--due-to YYYY-MM-DD] \
  [--custom-text customField1=value] \
  [--custom-option customField3=5] \
  [--with-children]
```

### Step 5: Present results

Read `assets/output-format.md` and follow it exactly. Render the full table with all columns
(ID, Type, Subject, Parent, Assignee, Responsible, Status, Start, Due, Work, Spent) grouped by
project. Apply ⚠️/🚨 flags. Indent children with `↳` when `--with-children` was used.
Do not simplify or drop columns — the user expects the full detail every time.

## Scripts

### `search_work_packages.py`

```bash
python3 <skill_path>/scripts/search_work_packages.py [flags]
```

**Filter flags** (all optional; combine freely as AND):

| Flag | Effect |
|------|--------|
| `--project ID` | Scope to one project |
| `--subject TEXT` | Subject contains TEXT (case-insensitive substring) |
| `--id 123,456` | Fetch specific work package IDs |
| `--assignee USER_ID` | Assigned to this user |
| `--responsible USER_ID` | Accountable/responsible user |
| `--status 1,7,13` | Comma-separated status IDs |
| `--status-open` | All non-closed statuses (overrides `--status`) |
| `--type 1,4,5` | Comma-separated type IDs |
| `--start-from DATE` | startDate >= DATE (can combine with --start-to) |
| `--start-to DATE` | startDate <= DATE (can combine with --start-from) |
| `--due-from DATE` | dueDate >= DATE (can combine with --due-to) |
| `--due-to DATE` | dueDate <= DATE (can combine with --due-from) |
| `--custom-text KEY=VALUE` | customFieldN contains VALUE (text fields) |
| `--custom-option KEY=ID` | customFieldN equals option ID (list fields) |
| `--with-children` | Also fetch direct children of matched items (1 level) |

Output: JSON `{"total": N, "items": [...]}` where each item has `id`, `subject`, `type`, `status`, `project`, `assignee`, `responsible`, `startDate`, `dueDate`, `work`, `spent`, `parent`, `link`, `children`.

## Output

Read `assets/output-format.md` for the full spec — it defines every column, flag, and grouping
rule. Always follow it exactly; never present a simplified table with fewer columns.

Summary:
- **Header**: `Found N work packages [matching: filter summary]`
- **Grouped by project** with item count per group
- **Columns**: ID (linked) | Type | Subject | Parent | Assignee | Responsible | Status | Start | Due | Work | Spent
- **Children** indented with `↳` prefix when `--with-children` was used
- **Flags**: `⚠️` on missing Start/Due/Work; `🚨` on overdue Due or Spent > Work
- Omit Responsible only if no items have one; omit Parent only if no items have one

## Notes

- **responsible vs assignee**: OpenProject has two person fields per work package. `assignee` = who does the work; `responsible` = who is accountable for it. Both are independently filterable.
- **`--with-children` scope**: Only direct children of matched items are fetched — not grandchildren. The children are not filtered by the original search criteria; all direct children are included.
- **No filters = all work packages**: Running the script with no flags (except perhaps `--project`) returns everything. Always scope with at least one filter unless a full dump is intended.
- **Custom field filter operators**: Text custom fields use `~` (contains); list-type custom fields use `=` with the option numeric ID. The option ID comes from `allowedValues[].id` in the cached custom fields file.
- **Date range for "active in period"**: To find work packages active within a period, combine `--start-from` and `--due-to` (items that started before the period ends and end after it starts).

## Memory

- `.memory/users/directory.json` — cached user name → ID mappings; check before calling find-user
- `.memory/statuses/list.json` — all status name → ID mappings
- `.memory/types/list.json` — all type name → ID mappings
- `.memory/custom-fields/global.json` — global custom fields (WBS, Task ID, Task Type, Earned Story Points); check first, re-fetch only on API error
- `.memory/projects/{slug}/custom-fields.json` — project-specific custom fields only (excludes global fields); TTL 90 days

## Related Skills

- **find-user** — resolves assignee/responsible name to numeric user ID (Step 1)
- **query-user-status** — faster alternative when you just want one user's open tasks (no custom filters needed)
