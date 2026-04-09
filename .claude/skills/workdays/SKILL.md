---
name: workdays
description: Date utilities for checking workdays, calculating working days, and date arithmetic. Supports configurable work week and national holiday caching. Use when the user asks about dates, working days, deadlines, due dates, task scheduling, or day-of-week checks.
---

# Date Calculations

## Purpose

Performs working-day-aware date math: due dates from hour estimates, sequential task scheduling, working day counts, and range lookups. Accounts for weekends (configurable) and public holidays (cached in `.memory/`). Used as a dependency by other skills that need date ranges or deadlines.

## Workflow

### Step 1: Determine which years are needed

Look at the dates in the user's request and identify which calendar years are involved (a date range may span two years).

### Step 2: Check holiday cache

```bash
python3 <skill_path>/scripts/dates.py cache-status <YEAR> [YEAR2]
```

Outputs JSON: `[{"year": 2026, "status": "missing", "age_days": null}]`

Status values: `fresh` (use as-is), `stale` (needs refresh), `missing` (never fetched).

### Step 3: Refresh stale or missing years via web search

For any year that is not `fresh`, use the `holiday_search_query` from `.memory/settings/workweek.json` (replace `{year}`) to find the official holiday list.

Extract all public holidays. Write the cache file:

**Path:** `.memory/holidays/{year}.json`
**Format:** `[{"date": "YYYY-MM-DD", "name": "Holiday Name"}, ...]`

Only list dates that fall on workdays — weekend days are already excluded by config. After writing, update the Holidays table in `.memory/index.md`.

**Cache rules:**
- Past years: cached permanently
- Current year: expires after 30 days (lunar-calendar holidays get confirmed late in the year)

### Step 4: Run the script

```bash
python3 <skill_path>/scripts/dates.py <command> <args>
```

The script reads the holiday cache and work week config automatically.

## Commands

| Command | Usage | Output |
|---------|-------|--------|
| `is-workday` | `is-workday 2026-03-26` | "Public holiday" / "Working day (Wednesday)" |
| `add` | `add 2026-03-10 2` | `2026-03-12` |
| `prev` | `prev 2026-04-08 3` | `2026-04-05` |
| `due` | `due 2026-03-10 16` | `{"start":"...","due":"...","workingDays":2}` |
| `schedule` | `schedule 2026-03-10 16 8 24` | JSON array of tasks with start/due per task |
| `count` | `count 2026-03-01 2026-03-31` | `{"workingDays":N,"calendarDays":31,...}` |

## Examples

```bash
# Is March 26 a workday?
python3 scripts/dates.py is-workday 2026-03-26
# → Public holiday (Independence Day)

# Due date for 24h of work starting Apr 9
python3 scripts/dates.py due 2026-04-09 24
# → {"start":"2026-04-09","due":"2026-04-15","workingDays":3}

# Schedule 3 tasks sequentially
python3 scripts/dates.py schedule 2026-03-10 16 8 16
# → [{"task":1,"start":"2026-03-10","due":"2026-03-12",...}, ...]

# Count working days in a month
python3 scripts/dates.py count 2026-04-01 2026-04-30
# → {"start":"2026-04-01","end":"2026-04-30","workingDays":21,"calendarDays":30}

# "Last 3 working days" range (today = 2026-04-08 Wed)
python3 scripts/dates.py prev 2026-04-08 3  # → 2026-04-05 (start)
python3 scripts/dates.py prev 2026-04-08 1  # → 2026-04-07 (end)
```

## Memory

### Work Week Config — `.memory/settings/workweek.json`

Read at startup by the script. Controls weekend days, hours/day, and the holiday search query.

```json
{
  "country": "Bangladesh",
  "workdays": [6, 0, 1, 2, 3],
  "weekend": [4, 5],
  "hours_per_day": 8,
  "holiday_search_query": "Bangladesh public holidays {year} official gazette site:mopa.gov.bd OR site:cabinet.gov.bd OR site:thedailystar.net",
  "notes": "Python weekday(): Mon=0 Tue=1 Wed=2 Thu=3 Fri=4 Sat=5 Sun=6"
}
```

If the file is missing, the script falls back to Bangladesh defaults (weekend=[4,5], 8h/day). To switch to a Mon–Fri team: set `"weekend": [5, 6]` and update `workdays` to `[0,1,2,3,4]`.

### Holiday Cache — `.memory/holidays/{year}.json`

```json
[
  {"date": "2026-03-26", "name": "Independence Day"},
  {"date": "2026-04-14", "name": "Pahela Baishakh (Bangla New Year)"}
]
```

- Only workday dates listed (weekend days excluded by config)
- Sorted ascending by date
- The script silently skips holidays for uncached years (won't error out), so always complete Step 3 before calculating across missing years
