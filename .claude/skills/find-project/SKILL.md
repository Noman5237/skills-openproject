---
name: find-project
description: Searches OpenProject projects by name or identifier and resolves them to numeric IDs. Also fetches and caches project-specific custom field schemas. Use this skill whenever the user asks to find a project, look up a project ID, list projects, needs a project ID for other operations, or wants to know what custom fields a project has. Trigger on phrases like "find project", "which project", "project ID", "list projects", "what projects do we have", "project custom fields", or any time you need to resolve a project name to an ID.
---

# Finding Projects

## Purpose

Resolves project names to numeric OpenProject project IDs and caches the results. Many other skills (search-work-packages, create-work-packages, update-work-packages, query-user-costs) need a numeric project ID — this skill is the standard lookup step. It can also fetch and cache a project's custom field schema, which create/update skills need to set project-specific fields correctly.

## Workflow

### Step 1: Check the cache

Before calling the API, check `.memory/projects/*/meta.json` for a cached project matching the name. Project IDs are stable — a cached ID is reliable unless the lookup returns 404.

### Step 2: Search by name

If not cached, run the search script. It auto-populates `meta.json` for every result.

```bash
python3 <skill_path>/scripts/search_project.py <name>
```

### Step 3: Fetch and cache custom fields

Always check whether the project's custom fields are already cached. This keeps the cache warm so that downstream skills (create/update work packages) don't have to fetch schemas on the fly.

Check `.memory/projects/{slug}/custom-fields.json`:
- If it exists and `meta.lastUpdated` is within 90 days, report the cached fields
- If missing or stale, run:

```bash
python3 <skill_path>/scripts/get_project.py <project_id> --schema
```

This fetches the schema, excludes global fields, and caches the result. Always include the custom fields (or "no project-specific fields") in your response so the user knows what's available.

## Scripts

All scripts require `OPENPROJECT_API_KEY` to be set (auto-loaded from `.env`). Only standard library modules are used.

### Search by Name

```bash
python3 <skill_path>/scripts/search_project.py <name>
python3 <skill_path>/scripts/search_project.py <name> --cache-dir /path/to/.memory/projects
```

### Get Project by ID

```bash
python3 <skill_path>/scripts/get_project.py <project_id>
python3 <skill_path>/scripts/get_project.py <project_id> --schema
python3 <skill_path>/scripts/get_project.py <project_id> --schema --type 1,4,6
```

`--type` specifies which work package type IDs to check for custom fields (default: 1,6 = Task, User Story). Pass additional type IDs if the project uses custom fields on other types.

## Output

**Search result (search_project.py):**
```json
[{"id": 41, "name": "CityRemit CR", "identifier": "cityremit-cr", "status": "on track"}]
```

**Project detail (get_project.py):**
```json
{"id": 41, "name": "CityRemit CR", "identifier": "cityremit-cr", "description": "...", "status": "on track", "public": false}
```

**Project detail with schema (get_project.py --schema):**
```json
{
  "id": 41, "name": "CityRemit CR", "identifier": "cityremit-cr",
  "description": "...", "status": "on track", "public": false,
  "customFields": [
    {"fieldKey": "customField8", "label": "Branch Name", "type": "text", "required": false, "allowedValues": null, "notes": ""}
  ]
}
```

Empty array `[]` from search means no match — try a shorter substring.

## Notes

- `name_and_identifier` filter matches against both the project's display name and its URL slug
- `~` operator = substring match (case-insensitive)
- Project IDs are stable identifiers — cached IDs are reliable
- The `--schema` flag on `get_project.py` merges custom fields from multiple work package types (deduped by fieldKey) and excludes global fields already in `.memory/custom-fields/global.json`

## Memory

### Project meta — `.memory/projects/{slug}/meta.json`

Auto-created by both `search_project.py` and `get_project.py`. Contains project ID, name, identifier, status, and cache date.

```json
{"id": 41, "name": "CityRemit CR", "identifier": "cityremit-cr", "status": "on track", "cachedAt": "2026-04-09"}
```

To look up a project ID from cache, read the `meta.json` files under `.memory/projects/`.

### Custom fields — `.memory/projects/{slug}/custom-fields.json`

Created by `get_project.py --schema`. Contains only project-specific custom fields (global fields excluded). TTL: 90 days. Re-fetch if API rejects a field key or option ID.

After a successful lookup, update the Projects table in `.memory/index.md`.

## Related Skills

- **search-work-packages** — uses project ID to scope work package searches
- **create-work-packages** — needs project ID and custom field schema to create items
- **update-work-packages** — needs custom field schema to set project-specific fields
- **find-user** — analogous skill for resolving user names to IDs
