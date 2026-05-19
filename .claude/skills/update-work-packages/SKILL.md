---
name: update-work-packages
description: Updates or deletes existing OpenProject work packages — set assignee, accountable/responsible, status, estimated work (hours), start date, due date, subject (name), WBS, or any project-specific custom field, in any combination, on one or many work packages at once. Can also post comments on work packages. Also handles deletion of work packages (including parent+children hierarchies). Use this skill whenever the user wants to change, edit, reassign, reschedule, rename, bulk-update, delete, or remove work packages, or add a comment/note to a work package. Trigger on phrases like "assign #123 to Noman", "mark these tasks as In progress", "set due date", "update WBS", "change status of", "reassign", "reschedule", "delete this task", "remove these work packages", "add a comment", "leave a note on", "ask why this is on hold", or any request to modify, delete, or comment on existing work packages.
---

# Updating & Deleting Work Packages

## Purpose

PATCHes one or many existing work packages in OpenProject. Any combination of fields can be updated in a single call. Handles OpenProject's optimistic locking automatically (fetches `lockVersion` before each PATCH).

Also supports **posting comments** on work packages — standalone or alongside field updates.

Also supports **deleting** work packages — single items or entire hierarchies (parent + children).

## Workflow

### Step 1: Identify target work packages

The user typically provides work package IDs directly (e.g. `#59487`, `#59488`). If they describe work packages by subject or filter instead, use the **search-work-packages** skill first to find the relevant IDs.

**Dates and work apply to Tasks only.** When the user asks to set `estimatedHours`, `startDate`,
or `dueDate`, apply these to Task-type items only. Epic, Feature, and User Story levels derive
their dates and work automatically from their child Tasks — setting them directly on parents is
ineffective and will be overridden. If the user references a parent item with these fields,
identify and update its child Tasks instead.

### Step 2: Resolve names to IDs

Translate any human-readable names to numeric IDs:
- **Assignee / responsible names** → check `.memory/users/directory.json`; if not cached, use the **find-user** skill
- **Status names** → read `.memory/statuses/list.json` (e.g. "In progress" → 7, "New" → 1)
- **Type names** → read `.memory/types/list.json` (e.g. "Task" → 1, "User story" → 6)

**Schedule dates and check overload.** If `estimatedHours` and an assignee are being set:
- **No dates provided** — call the **assign-work-packages** skill to compute `startDate` and `dueDate`. Use the computed dates in Step 5.
- **Explicit dates provided** — call the **assign-work-packages** skill with `--start <startDate>` to run an overload check on those dates. If conflicts are found, surface them in the Step 4 preview and ask the user whether to proceed before running the script.

### Step 3: Check custom fields cache (only if updating custom fields)

If the user wants to update a custom field (e.g. WBS, Task Type), resolve its `fieldKey` and option IDs from two sources — merge both:

1. **Global fields** — read `.memory/custom-fields/global.json` (re-fetch only if API rejects a field key or option ID)
2. **Project-specific fields** — check `.memory/projects/{slug}/custom-fields.json`:
   - If it exists and `meta.lastUpdated` is within 90 days, use it
   - If missing or stale, fetch the schema: `python3 <project_root>/.claude/scripts/fetch_schema.py <project_id> <type_id>`, exclude any `fieldKey` already in `global.json`, and save the remainder

For list-type fields, use the option's `id` from `allowedValues` to build the href: `/api/v3/custom_options/{id}`

### Step 4: Preview and confirm

Read `assets/preview-format.md` for the full preview table spec, column definitions, field label
conventions, and how to show scheduling notes and overload alerts.

Build the preview from the resolved changes (human-readable names and values, not IDs), show it
to the user, then ask: "Proceed with these updates?" Only build the input JSON and run the script
after confirmation.

### Step 5: Build the input JSON

Write a file at `/tmp/wp_updates.json`. Include only the fields being changed — omit everything else.

```json
[
  {
    "id": 59487,
    "statusId": 7,
    "assigneeId": 64,
    "comment": "Moving to In progress — starting work today."
  },
  {
    "id": 59488,
    "dueDate": "2026-04-30",
    "estimatedHours": 8,
    "fields": { "customField1": "OPS-012" },
    "links": { "customField3": "/api/v3/custom_options/1" }
  },
  {
    "id": 59489,
    "comment": "Why is this task on hold? Please clarify."
  }
]
```

**Available fields per update item** (all optional except `id`):

| Field | Type | Maps to |
|-------|------|---------|
| `id` | integer | Work package ID (required) |
| `subject` | string | Subject/name |
| `description` | string | Description body (rendered as markdown) |
| `startDate` | `YYYY-MM-DD` | Start date |
| `dueDate` | `YYYY-MM-DD` | Due/finish date |
| `estimatedHours` | number | Estimated work (converted to `PT{H}H{M}M`) |
| `assigneeId` | integer | `_links.assignee` |
| `responsibleId` | integer | `_links.responsible` (accountable) |
| `statusId` | integer | `_links.status` |
| `comment` | string | Posted as an activity comment on the WP (plain text or markdown) |
| `fields` | object | Plain-value custom fields (text, integer, float) |
| `links` | object | List-type custom fields → `{fieldKey: "/api/v3/custom_options/{id}"}` |
| `relations` | array | Create relations (dependencies) to other work packages — see below |

**Relation format** (each entry in `relations`):

```json
{"type": "blocked_by", "targetId": 60352}
```

| `type` value | Meaning |
|---|---|
| `blocks` | this WP blocks the target |
| `blocked_by` | this WP is blocked by the target |
| `relates` | this WP relates to the target |
| `precedes` | this WP precedes the target |
| `follows` | this WP follows the target |
| `duplicates` | this WP duplicates the target |
| `duplicated_by` | this WP is duplicated by the target |

Relations appear in `changed_fields` as `relation:blocked_by:#60352`.

### Step 6: Run the script

```bash
python3 <skill_path>/scripts/update_work_packages.py --input /tmp/wp_updates.json
```

The script fetches the current `lockVersion` for each WP (required by OpenProject), then PATCHes each one with only the specified fields.

### Step 7: Report results

Parse the JSON output and present results using the format in `assets/output-format.md`. Summary:
- **Header**: `Updated N work packages:`
- **Table**: ID (linked) | Type | Subject | Assignee | Start | Due | Work | Status | Changed (field names)
- **Errors** section (if any): list failed IDs with error and suggested fix — see **Error Handling** below

---

## Deletion Workflow

When the user asks to **delete** or **remove** work packages, follow this flow instead of the update workflow above.

### Step D1: Identify target work packages

Same as Step 1 — if the user describes work packages by name or filter, use **search-work-packages** with `--with-children` to find all IDs. Always expand children so you know the full hierarchy that will be deleted.

### Step D2: Preview and confirm

Show a deletion preview table listing every work package that will be deleted, with children indented under their parent:

| ID | Type | Subject |
|----|------|---------|
| [#59488](http://...) | Task | ↳ Dummy Task for Testing |
| [#59487](http://...) | User story | Dummy User Story for Testing |

Then ask: **"Delete these N work packages? This action is irreversible."**

Only proceed after the user confirms.

### Step D3: Build the input JSON

Write a file at `/tmp/wp_deletes.json` containing an array of work package IDs. **Children must come before parents** — the script deletes in the order given, so listing children first avoids issues with cascading or orphaned references.

```json
[59488, 59487]
```

### Step D4: Run the script

```bash
python3 <skill_path>/scripts/delete_work_packages.py --input /tmp/wp_deletes.json
```

### Step D5: Report results

Parse the JSON output. Present a summary table:

```
Deleted N work packages:
```

| ID | Type | Subject |
|----|------|---------|
| #59488 | Task | Dummy Task for Testing |
| #59487 | User story | Dummy User Story for Testing |

If errors occurred, list them:

```
**Failed (M):**
- #ID — <error message>
  Fix: <suggested action>
```

---

## Scripts

### `update_work_packages.py`

```bash
python3 <skill_path>/scripts/update_work_packages.py --input <json_file>
```

- Reads the update array from `--input`
- For each item: fetches current `lockVersion`, builds PATCH body with only specified fields, PATCHes the WP
- If `comment` is present, posts it as an activity after the PATCH (or standalone if no field changes)
- Outputs: `{"updated": [...], "total": N, "errors": [...]}`

Each entry in `updated` has: `id`, `subject`, `type`, `status`, `link`, `changed_fields` (includes `"comment"` when a comment was posted).

### `delete_work_packages.py`

```bash
python3 <skill_path>/scripts/delete_work_packages.py --input <ids.json>
```

- Reads an array of work package IDs from `--input`
- For each ID: fetches WP metadata (for reporting), then sends a DELETE request
- Outputs: `{"deleted": [...], "total": N, "errors": [...]}`

Each entry in `deleted` has: `id`, `subject`, `type`, `link`, `status` (HTTP status code, 204 = success).

## Memory

- `.memory/users/directory.json` — cached user name → ID mappings
- `.memory/statuses/list.json` — status name → ID mappings
- `.memory/types/list.json` — type name → ID mappings
- `.memory/custom-fields/global.json` — global custom fields (WBS, Task ID, Task Type, Earned Story Points); check first, re-fetch only on API error
- `.memory/projects/{slug}/custom-fields.json` — project-specific custom fields only (excludes global fields); TTL 90 days

## Notes

- **lockVersion**: OpenProject uses optimistic locking — each PATCH must include the `lockVersion` from the current state of the WP. The script fetches this automatically. If a 409 Conflict occurs, the WP was modified between the fetch and the PATCH; re-run the update.
- **Partial updates**: Only include fields that are actually changing. Sending an existing value is harmless but unnecessary.
- **responsible vs assignee**: `assigneeId` = who does the work; `responsibleId` = who is accountable for it.
- **Clearing a field**: To unassign a user or clear a date, pass `null` as the value (e.g. `"assigneeId": null` → `{"href": null}`).
- **Comments**: A `comment` can be included alongside field changes (posted after the PATCH) or on its own (no PATCH needed). Comments are posted via `POST /api/v3/work_packages/{id}/activities`. The comment text supports plain text or markdown.

## Error Handling

If the script output contains errors, list them after the table:

```
**Failed (M):**
- #ID — <error message>
  Fix: <suggested action>
```

Common causes and fixes:

| Error | Cause | Fix |
|-------|-------|-----|
| 409 Conflict | lockVersion mismatch (WP modified concurrently) | Re-run the update |
| 422 Unprocessable | Invalid field value or custom_option ID | Check `.memory/projects/{slug}/custom-fields.json` |
| 404 Not Found | WP ID does not exist or is not accessible | Verify the ID |

## Related Skills

- **search-work-packages** — find WP IDs by filter before updating (Step 1)
- **find-user** — resolve assignee/responsible name to numeric user ID (Step 2)
