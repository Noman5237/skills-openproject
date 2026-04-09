---
name: create-work-packages
description: Creates OpenProject work packages — single items or full hierarchies (Epic → Feature → User Story → Task, or any subset). Use this skill whenever the user wants to create tasks, add work packages, set up an epic or sprint breakdown, bulk-create user stories with sub-tasks, or add any work items to an OpenProject project. Trigger on phrases like "create task", "add work package", "set up epic", "create user stories", "bulk create", "create sprint items", "add features to epic", or any request to add project work items.
---

# Creating Work Packages

## Purpose

Creates one or many work packages in OpenProject, preserving parent-child hierarchy (Epic → Feature → User Story → Task or any subset). Discovers and caches project-specific custom fields the first time you create items in a project, so subsequent creations are fast. Use whenever the user needs to add work items to any project.

## Workflow

### Step 1: Identify the project

If the user gives a project name or slug rather than a numeric ID, look it up:

```bash
python3 -c "
import base64, json, os, sys, urllib.parse, urllib.request
key = os.environ['OPENPROJECT_API_KEY']
creds = base64.b64encode(f'apikey:{key}'.encode()).decode()
base = os.environ.get('OPENPROJECT_BASE_URL', 'http://project.global.fintech23.xyz').rstrip('/')
name = sys.argv[1]
filters = urllib.parse.quote(json.dumps([{'name':{'operator':'~','values':[name]}}]))
url = f'{base}/api/v3/projects?filters={filters}'
req = urllib.request.Request(url, headers={'Authorization': f'Basic {creds}'})
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())
for e in data['_embedded']['elements']:
    print(e['id'], e['identifier'], e['name'])
" "PROJECT_NAME"
```

Note the numeric `id` and `identifier` (slug).

### Step 2: Check and refresh custom fields cache

Custom fields come from two sources — always merge both:

1. **Global fields** — read `.memory/custom-fields/global.json` (always present, no staleness check)
2. **Project-specific fields** — check `.memory/projects/{slug}/custom-fields.json`:
   - If the file exists and `meta.lastUpdated` is within 90 days — use it as-is
   - If missing or stale — fetch schema for each distinct type you'll create:
     ```bash
     python3 <project_root>/.claude/scripts/fetch_schema.py <project_id> <type_id>
     ```
     Run once per type (e.g. type 5 for Epic, type 4 for Feature, type 1 for Task). From the output, **exclude any `fieldKey` already in `global.json`**, then merge and save to `.memory/projects/{slug}/custom-fields.json`. Update the Projects — Custom Fields table in `.memory/index.md`.

### Step 3: Collect work package details

Only include a field in the input if the user explicitly provided it, or its value can be unambiguously inferred from context (e.g. the assignee was named, the type was stated). Never guess or invent values for fields.

**Always required — must be provided or asked:**
- **Subject** (title) for each item
- **Type** — map name to ID using `.memory/types/list.json` (Epic=5, Feature=4, User story=6, Task=1, Bug=7)
- **Required custom fields** (from the cached schema) — if not provided and not clearly inferable, stop and ask. For list-type fields, show the allowed values and let the user pick. For WBS (customField1), follow the convention in `.memory/custom-fields/global.json` notes.

**Only include if explicitly provided or clearly implied by context:**
- Start / Due date
- Estimated hours
- Assignee (use the find-user skill to resolve a name to ID)
- Status (omit to let OpenProject default to New)
- Optional custom fields

For hierarchy: understand which items are parents of which. The script creates parents first and automatically sets the parent link on children.

### Step 4: Build the input JSON

For WBS (customField1), follow the convention in `.memory/custom-fields/global.json` notes — compute the WBS assignments for every item first.

**Schedule dates and check overload.** For any Task-type item with `estimatedHours` and an assignee:
- **No dates provided** — call the **assign-work-packages** skill to compute `startDate` and `dueDate`. Pass `--project PROJECT_ID` to scope the schedule lookup.
- **Explicit dates provided** — call the **assign-work-packages** skill with `--start <startDate>` to run an overload check on those dates. If conflicts are found, surface them in the preview and ask the user whether to proceed before building the JSON.

**Preview and confirm before creating.** Read `assets/preview-format.md` for the full preview
table spec, column definitions, how to show scheduling notes and overload alerts, and the
confirmation prompt. Show the preview, then wait for the user to confirm before proceeding.

Write the file at `/tmp/wp_hierarchy.json`. Separate custom field values from custom field links:
- `fields`: plain-value custom fields (text, integer, float)
- `links`: list-type custom fields, where value is the full href (e.g. `/api/v3/custom_options/5`)

```json
{
  "projectId": 5,
  "items": [
    {
      "subject": "Epic: User Authentication",
      "typeId": 5,
      "startDate": "2026-04-15",
      "dueDate": "2026-05-30",
      "estimatedHours": 80,
      "assigneeId": 64,
      "statusId": 6,
      "fields": { "customField1": "1.0" },
      "links": { "customField3": "/api/v3/custom_options/12" },
      "children": [
        {
          "subject": "Feature: Login with email/password",
          "typeId": 4,
          "fields": { "customField1": "1.1" },
          "links": { "customField3": "/api/v3/custom_options/1" },
          "children": [
            {
              "subject": "Task: Create login API endpoint",
              "typeId": 1,
              "estimatedHours": 8,
              "fields": { "customField1": "1.1.1" },
              "links": { "customField3": "/api/v3/custom_options/1" }
            }
          ]
        }
      ]
    }
  ]
}
```

All fields except `subject`, `typeId`, and `projectId` are optional. Omit any that aren't relevant.

### Step 5: Create the work packages

```bash
python3 <skill_path>/scripts/create_work_packages.py --input /tmp/wp_hierarchy.json
```

The script creates items depth-first (each parent before its children), sets parent links automatically, and outputs JSON with all created IDs and links.

### Step 6: Report results

Parse the output and present results using the format in `assets/output-format.md`. Summary:
- **Header**: `Created N work packages in "project-name":`
- **Table**: ID (linked) | Type | Subject (children indented with `↳`) | Assignee | Start | Due | Work | Status — parents before children (depth-first order)
- **Errors** section (if any): list failed items with error message and suggested fix — see **Error Handling** below

## Scripts

### `fetch_schema.py` (shared utility)

```bash
python3 <project_root>/.claude/scripts/fetch_schema.py <project_id> <type_id>
```

- Calls `GET /api/v3/work_packages/schemas/{project_id}-{type_id}`
- Extracts all `customField*` keys with name, type, required, and allowed values
- Outputs: `{"customFields": [...]}`

Shared script in `.claude/scripts/` — also used by `search-work-packages`. Run once per type; merge the output into `.memory/projects/{slug}/custom-fields.json`.

### `create_work_packages.py`

```bash
python3 <skill_path>/scripts/create_work_packages.py --input <json_file>
```

- Reads the hierarchy JSON from `--input`
- Creates items depth-first; children receive their parent's ID automatically
- Outputs: `{"created": [...], "total": N, "errors": [...]}`

Each entry in `created` has: `id`, `subject`, `type`, `link`, `children`.

## Memory

### Custom Fields

- **Global** — `.memory/custom-fields/global.json`: WBS, Task ID, Task Type, Earned Story Points. Always check this first; re-fetch only on API error (rejected field key or option ID).
- **Project-specific** — `.memory/projects/{slug}/custom-fields.json`: fields unique to the project. TTL: 90 days. Contains only non-global fields. Re-fetch if API returns 422 on an unknown field/option.

After saving a per-project file, update the Projects — Custom Fields table in `.memory/index.md`.

### Type IDs — `.memory/types/list.json`

All type name → ID mappings. Key ones: Epic=5, Feature=4, User story=6, Task=1, Bug=7.

### Status IDs — `.memory/statuses/list.json`

Default for new items: **New (1)**. Common alternatives: To be scheduled (5), Scheduled/To Do (6), In progress (7).

## Error Handling

If the script output contains errors, list them after the table:

```
**Failed (M):**
- "Subject of failed item" — <error message>
  Fix: <suggested action>
```

Common causes and fixes:

| Error | Cause | Fix |
|-------|-------|-----|
| 422 with unknown field | Stale or missing custom fields cache | Re-fetch schema: `python3 .claude/scripts/fetch_schema.py <project_id> <type_id>` |
| 422 with invalid custom_option ID | Option ID no longer valid | Check `allowedValues` in `.memory/projects/{slug}/custom-fields.json` |
| 404 on project/type/assignee | Incorrect numeric ID | Verify the ID is correct |

## Related Skills

- **find-user** — resolves assignee name to numeric user ID (Step 3)
- **workdays** — calculates start/due dates from hour estimates and the team's working-day calendar (Step 3)
