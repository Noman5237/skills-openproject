---
name: add-user-to-project
description: Adds an OpenProject user to a project as a member with a specified role. Use this skill whenever the user wants to add someone to a project, grant project access, manage project membership, or when a task assignment fails because the user isn't a project member. Trigger on phrases like "add user to project", "grant access", "add member", "can't assign — not a member", or any request to manage project memberships.
---

# Adding Users to Projects

## Purpose

Adds a user as a member of an OpenProject project with a specified role. This is needed when
someone needs to be assigned tasks in a project they aren't yet part of — OpenProject blocks
assignment of non-members. Also useful for onboarding team members to new projects.

## Workflow

### Step 1: Resolve the user

If the user gives a name (not a numeric ID), check `.memory/users/directory.json` first. If
not cached, use the **find-user** skill to get their numeric user ID.

### Step 2: Resolve the project

If the user gives a project name (not a numeric ID), use the **find-project** skill to get the
numeric project ID.

### Step 3: Determine the role

Default role is **Member** (ID: 6), which is appropriate for most cases. If the user specifies
a different role, map it using the table below.

| ID | Role |
|----|------|
| 1  | Work package editor |
| 2  | Work package commenter |
| 3  | Work package viewer |
| 6  | Member |
| 7  | Reader |
| 8  | Project admin |

If unsure which role to use, ask the user. For typical task assignment scenarios, Member is correct.

### Step 4: Preview and confirm

Show what will happen before proceeding:

```
Add **User Name** to **Project Name** as **Role Name**. Proceed?
```

### Step 5: Run the script

```bash
python3 <skill_path>/scripts/add_member.py --user-id USER_ID --project-id PROJECT_ID [--role-id ROLE_ID]
```

### Step 6: Report results

On success:
```
Added **User Name** to **Project Name** as **Member**.
```

On error, show the error message and suggest a fix (see Error Handling below).

## Additional Commands

### List project members

```bash
python3 <skill_path>/scripts/add_member.py --list-members --project-id PROJECT_ID --user-id 0
```

### List available roles

```bash
python3 <skill_path>/scripts/add_member.py --list-roles --user-id 0 --project-id 0
```

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| 422 User is already a member | User already belongs to this project | No action needed — they can already be assigned |
| 403 Forbidden | API user lacks permission to manage memberships | Contact a project admin |
| 404 Not Found | Invalid user ID or project ID | Verify the IDs with find-user / find-project |

## Memory

- `.memory/users/directory.json` — cached user name to ID mappings

## Related Skills

- **find-user** — resolves user name to numeric ID (Step 1)
- **find-project** — resolves project name to numeric ID (Step 2)
- **update-work-packages** — may trigger this skill when assignment fails due to non-membership
- **create-work-packages** — may trigger this skill when assignee is not a project member
