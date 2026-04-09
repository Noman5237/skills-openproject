---
name: find-user
description: Searches OpenProject users and principals by name. Use when the user asks to find a team member, look up a user ID, or needs a user ID for various tasks.
---

# Searching Users

## Purpose

Resolves human names to numeric OpenProject user IDs. Skills that filter by assignee, log time, or query tasks all need a numeric ID first — this skill is the standard lookup step before those operations. Check `.memory/users/directory.json` before calling the API.

## Scripts

All scripts require `OPENPROJECT_API_KEY` to be set. Only standard library modules are used.

### Search by Name
```bash
python3 <skill_path>/scripts/search_user.py <name>              # all principals
python3 <skill_path>/scripts/search_user.py <name> --users-only  # users only
```

### Get User by ID
```bash
python3 <skill_path>/scripts/get_user.py <user_id>
```

## Output

**Search result (search_user.py):**
```json
[{"id": 64, "name": "Md. Abdullah Al Noman", "type": "User"}]
```

**User detail (get_user.py):**
```json
{"id": 64, "name": "Md. Abdullah Al Noman", "login": "abdullah.noman@brainstation-23.com", "email": "abdullah.noman@brainstation-23.com", "status": "active", "admin": false}
```

Empty array `[]` means no match — try a shorter name substring.

## Notes

- Use `principals` endpoint (not `users`) for search — it supports name filtering and includes users, groups, and placeholder users
- Filter by `type=User` to exclude groups and placeholder users
- `"me"` can be used as a filter value on other endpoints (time_entries, work_packages) to refer to the authenticated user
- `~` operator = substring match; `=` exact; `!` not equal
- User IDs are needed for: filtering time entries, assigning work packages, listing another user's tasks

## Memory

Before calling the API, check `.memory/users/directory.json` for a cached entry matching the name. User IDs are stable identifiers — a cached ID is reliable unless the lookup returns 404.

After a confirmed lookup, add the user to `.memory/users/directory.json` and update the Users table in `.memory/index.md`:

```json
[
  {"id": 64, "name": "Md. Abdullah Al Noman", "login": "abdullah.noman@brainstation-23.com", "cachedAt": "2026-04-08"}
]
```
