# OpenProject Memory Index

Base URL: http://project.global.fintech23.xyz

Claude Code reads this index at the start of each task to determine what is already known.
Update the relevant table row whenever you write a sub-file.

---

## Settings

| File | Last Updated | Notes |
|------|--------------|-------|
| settings/workweek.json | 2026-04-08 | Bangladesh: Sun–Thu workdays, Fri–Sat weekend, 8h/day |

**`settings/workweek.json`** controls the work week for all date calculations. Edit this file to adapt the skills to a different team's schedule (e.g., Mon–Fri). The `workdays` script reads it automatically; if missing, it falls back to Bangladesh defaults.

---

## Holidays

| Year | Path | Status | Last Updated | Notes |
|------|------|--------|--------------|-------|
| 2026 | holidays/2026.json | fresh | 2026-04-08 | 19 holidays |

TTL: past years = permanent; current year = stale after 30 days.
Status values match `cache-status` output: `fresh`, `stale`, `missing`.

---

## Global Custom Fields

| Path | Last Updated | Notes |
|------|--------------|-------|
| custom-fields/global.json | 2026-04-09 | 4 fields: WBS (cf1), Task ID (cf2), Task Type (cf3), Earned Story Points (cf6) |

Fields marked "available for all existing and new projects" in OpenProject admin — present in every project regardless of configuration. Always read this file before checking per-project custom fields. Re-fetch only if the API rejects a field key or option ID.

---

## Projects

Each project has a directory at `.memory/projects/{slug}/` containing:
- `meta.json` — project ID, name, identifier, status, cache date (auto-created by `find-project` skill)
- `custom-fields.json` — project-specific custom fields (auto-created by `get_project.py --schema`)

To look up a project ID from cache, read the `meta.json` files.

### Project Directory

| Project Slug | meta.json | custom-fields.json | Last Updated | Notes |
|-------------|-----------|-------------------|--------------|-------|
| cityremit-cr | yes | yes (1 field) | 2026-04-09 | Branch Name (customField8) |
| devops-support | yes | yes (0 fields) | 2026-04-09 | No project-specific fields |

### Custom Fields

Schema source: `GET /api/v3/work_packages/schemas/{project_id}-{type_id}`
Re-fetch if: API returns 422 with an unknown field or invalid custom_option ID, or `lastUpdated` is more than 90 days ago.

**When saving a per-project custom fields file:**
- Exclude any `fieldKey` already present in `custom-fields/global.json`
- Write `"customFields": []` if no project-specific fields remain (the `meta.lastUpdated` still signals the cache is fresh)

Per-project meta format (`meta.json`):
```json
{"id": 41, "name": "CityRemit CR", "identifier": "cityremit-cr", "status": "on track", "cachedAt": "2026-04-09"}
```

Per-project custom fields format (`custom-fields.json`):
```json
{
  "meta": {
    "lastUpdated": "YYYY-MM-DD",
    "typesChecked": [1, 6],
    "source": "GET /api/v3/work_packages/schemas/{project_id}-{type_id}",
    "notes": "Global fields excluded -- see custom-fields/global.json"
  },
  "customFields": []
}
```

---

## Users

| Path | Last Updated | Count |
|------|--------------|-------|
| users/directory.json | 2026-04-09 | 2 |

User IDs are stable — cache indefinitely, re-fetch only on 404.

Format: `.memory/users/directory.json`
```json
[{"id": 64, "name": "Md. Abdullah Al Noman", "login": "abdullah.noman@brainstation-23.com", "cachedAt": "2026-04-08"}]
```

---

## Statuses

| Path | Last Updated | Notes |
|------|--------------|-------|
| statuses/list.json | 2026-04-08 | 16 statuses; migrated from query-user-status SKILL.md |

Re-fetch only if API rejects a status ID.

---

## Types

| Path | Last Updated | Notes |
|------|--------------|-------|
| types/list.json | 2026-04-08 | 9 types; migrated from query-user-status SKILL.md |

---

## Activities (Time Entry)

| Path | Last Updated | Notes |
|------|--------------|-------|
| time-entries/activities.json | 2026-04-08 | |

---

## Priorities

| Path | Last Updated | Notes |
|------|--------------|-------|
