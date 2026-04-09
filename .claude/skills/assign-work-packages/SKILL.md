---
name: assign-work-packages
description: Computes the earliest available start date and due date for a new task assigned to a specific person, by finding their last scheduled task's end date and placing the new one immediately after. Flags any days where combined work would exceed 8h. Use this skill whenever you need to schedule a task for someone without an explicit date — triggered by phrases like "assign a task to Noman", "when can X start this", "find the next available slot for", "calculate due date given assignee and hours", or any time assignee + hours are provided without explicit due date in create or update workflows.
---

# Scheduling a Task

## Purpose

Places a new task into an assignee's schedule automatically: finds their last scheduled open
task, starts the new task on the next workday after it, and computes the due date from the
estimated hours. Also detects overload — days where the combined work from all tasks exceeds
8 hours — and surfaces those as alerts. Acts as a helper called from other skills, but can
also be invoked directly.

## Workflow

### Step 1: Resolve assignee

Check `.memory/users/directory.json` for a cached entry matching the name. If not found, use
the **find-user** skill to get the numeric user ID.

### Step 2: Run the scheduling script

Run from the **project root** (so the script can find `.memory/holidays/` and `.memory/settings/`):

```bash
python3 <skill_path>/scripts/schedule_task.py \
  --assignee-id USER_ID \
  --hours HOURS \
  [--start YYYY-MM-DD]   # override computed start; overload check still runs
  [--project PROJECT_ID] # scope task search to one project
```

### Step 3: Check holiday cache (if needed)

The script uses the same holiday cache as the **workdays** skill. If the proposed dates fall
in an uncached year, run the **workdays** skill (Steps 1–3) to refresh the cache, then re-run.

### Step 4: Interpret and present the output

```json
{
  "startDate": "2026-04-10",
  "dueDate": "2026-04-10",
  "baselineTask": {"id": 59488, "subject": "Dummy Task", "dueDate": "2026-04-09"},
  "existingTasks": [...],
  "conflicts": [{"date": "2026-04-10", "totalHours": 12.0, "tasks": ["Some Task", "new task"]}]
}
```

Present the proposed schedule clearly, and flag any conflicts:

```
Proposed: 2026-04-10 → 2026-04-10  (follows "Dummy Task", due 2026-04-09)

⚠️  2026-04-10: 12.0h scheduled (Some Task, new task) — exceeds 8h/day
```

If there are conflicts, ask the user whether to proceed anyway or pick a different date before
using these values downstream.

## Notes

- **Baseline task**: The assignee's open Task (type=Task) with the latest `dueDate`. Tasks
  without a `dueDate` are excluded from scheduling but are still included in overload detection
  if they have a `startDate`.
- **No scheduled tasks**: If the assignee has no tasks with a `dueDate`, scheduling starts from
  today (or the next workday if today is a weekend/holiday).
- **Override start**: If the user provides a fixed start date, it is used as-is. The overload
  check still runs to catch conflicts.
- **Remaining hours**: Overload detection uses each existing task's remaining work
  (estimated − spent), not its full estimate. Tasks that are already fully logged don't
  contribute to overload.
- **Proration**: Remaining hours are distributed evenly across the task's working days.
  This approximates daily load — actual distribution may differ.
- **Hours per day**: Configured in `.memory/settings/workweek.json` (default: 8h). A 4h task
  on an 8h/day schedule fits in one day, so `startDate == dueDate`.

## Memory

- `.memory/users/directory.json` — cached user ID mappings
- `.memory/settings/workweek.json` — workday calendar (weekend, hours/day)
- `.memory/holidays/{year}.json` — public holiday cache

## Related Skills

- **find-user** — resolve assignee name to numeric user ID (Step 1)
- **workdays** — refresh holiday cache for uncached years (Step 3)
- **update-work-packages** — calls this skill when assignee + hours are given without a due date
- **create-work-packages** — calls this skill for task-level items without explicit due dates

