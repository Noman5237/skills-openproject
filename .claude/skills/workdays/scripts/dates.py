#!/usr/bin/env python3
"""Date calculation utilities for configurable work week.

Commands:
  cache-status <YEAR> [YEAR ...]   Check if holiday cache is fresh or needs refresh
  is-workday  <DATE>               Check if a date is a working day
  add         <DATE> <N>           Add N working days to a date
  due         <DATE> <HOURS>       Calculate due date from estimated hours
  schedule    <DATE> <H1> [H2 ...]  Schedule tasks sequentially for one person
  count       <START> <END>        Count working days in a range

All dates: YYYY-MM-DD format.
Holiday cache: .memory/holidays/<year>.json in the working directory.
Cache format:  [{"date": "YYYY-MM-DD", "name": "Holiday Name"}, ...]
Work week config: .memory/settings/workweek.json (weekend days + hours_per_day).
"""

import json
import os
import sys
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Work week config — loaded from .memory/settings/workweek.json
# Defaults: Bangladesh (Sun–Thu workdays, Fri–Sat weekend, 8h/day)
# ---------------------------------------------------------------------------

_SETTINGS_PATH = os.path.join(os.getcwd(), ".memory", "settings", "workweek.json")
_DEFAULT_WEEKEND = frozenset([4, 5])   # Fri=4, Sat=5 (Python weekday())
_DEFAULT_HOURS_PER_DAY = 8


def _load_config() -> tuple[frozenset, int]:
    """Return (weekend_days, hours_per_day) from memory config or defaults."""
    if os.path.exists(_SETTINGS_PATH):
        with open(_SETTINGS_PATH) as f:
            cfg = json.load(f)
        return frozenset(cfg.get("weekend", list(_DEFAULT_WEEKEND))), int(cfg.get("hours_per_day", _DEFAULT_HOURS_PER_DAY))
    return _DEFAULT_WEEKEND, _DEFAULT_HOURS_PER_DAY


_WEEKEND, _HOURS_PER_DAY = _load_config()

# ---------------------------------------------------------------------------
# Holiday cache — read-only; the skill workflow populates it via web search
# ---------------------------------------------------------------------------

_CACHE_DIR = os.path.join(os.getcwd(), ".memory", "holidays")
_CURRENT_YEAR_TTL_DAYS = 30  # current year cache expires after 30 days

_year_cache: dict[int, set] = {}


def _cache_path(year: int) -> str:
    return os.path.join(_CACHE_DIR, f"{year}.json")


def _cache_age_days(year: int) -> int | None:
    """Return age of cache file in days, or None if it doesn't exist."""
    p = _cache_path(year)
    if not os.path.exists(p):
        return None
    return (date.today() - date.fromtimestamp(os.path.getmtime(p))).days


def _cache_is_fresh(year: int) -> bool:
    age = _cache_age_days(year)
    if age is None:
        return False
    if year < date.today().year:
        return True  # past years never expire
    return age < _CURRENT_YEAR_TTL_DAYS


def _load_year(year: int) -> set:
    if year in _year_cache:
        return _year_cache[year]
    p = _cache_path(year)
    if os.path.exists(p):
        with open(p) as f:
            data = json.load(f)
        dates = {h["date"] for h in data}
    else:
        dates = set()  # no cache — proceed without holidays for this year
    _year_cache[year] = dates
    return dates


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def is_workday(d: date) -> bool:
    return d.weekday() not in _WEEKEND and d.isoformat() not in _load_year(d.year)


def add_workdays(start: date, n: int) -> date:
    current = start
    added = 0
    while added < n:
        current += timedelta(days=1)
        if is_workday(current):
            added += 1
    return current


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_cache_status(args):
    """Output JSON list of cache status per year."""
    years = [int(y) for y in args] if args else [date.today().year]
    result = []
    for year in years:
        age = _cache_age_days(year)
        if age is None:
            status = "missing"
        elif _cache_is_fresh(year):
            status = "fresh"
        else:
            status = "stale"
        result.append({"year": year, "status": status, "age_days": age})
    print(json.dumps(result))


def cmd_is_workday(args):
    d = date.fromisoformat(args[0])
    if is_workday(d):
        print(f"Working day ({d.strftime('%A')})")
        sys.exit(0)
    else:
        reason = "Public holiday" if d.isoformat() in _load_year(d.year) else f"Weekend ({d.strftime('%A')})"
        print(reason)
        sys.exit(1)


def cmd_add(args):
    start = date.fromisoformat(args[0])
    n = int(args[1])
    print(add_workdays(start, n).isoformat() if n > 0 else start.isoformat())


def cmd_prev(args):
    start = date.fromisoformat(args[0])
    n = int(args[1])
    current = start
    subtracted = 0
    while subtracted < n:
        current -= timedelta(days=1)
        if is_workday(current):
            subtracted += 1
    print(current.isoformat())


def cmd_due(args):
    start = date.fromisoformat(args[0])
    days = int(args[1]) // _HOURS_PER_DAY
    due = add_workdays(start, days) if days > 0 else start
    print(json.dumps({"start": start.isoformat(), "due": due.isoformat(), "workingDays": days}))


def cmd_schedule(args):
    start = date.fromisoformat(args[0])
    tasks, current = [], start
    for i, hours in enumerate([int(h) for h in args[1:]], 1):
        days = hours // _HOURS_PER_DAY
        task_start = current
        task_due = add_workdays(current, days) if days > 0 else current
        tasks.append({"task": i, "start": task_start.isoformat(), "due": task_due.isoformat(),
                      "hours": hours, "days": days})
        current = task_due
    print(json.dumps(tasks, indent=2))


def cmd_count(args):
    start, end = date.fromisoformat(args[0]), date.fromisoformat(args[1])
    count, current = 0, start
    while current <= end:
        if is_workday(current):
            count += 1
        current += timedelta(days=1)
    print(json.dumps({"start": start.isoformat(), "end": end.isoformat(),
                      "workingDays": count, "calendarDays": (end - start).days + 1}))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

COMMANDS = {
    "cache-status": (cmd_cache_status, "[YEAR ...]"),
    "is-workday":   (cmd_is_workday,   "<DATE>"),
    "add":          (cmd_add,          "<DATE> <N>"),
    "prev":         (cmd_prev,         "<DATE> <N>"),
    "due":          (cmd_due,          "<DATE> <HOURS>"),
    "schedule":     (cmd_schedule,     "<DATE> <H1> [H2 ...]"),
    "count":        (cmd_count,        "<START> <END>"),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}\nAvailable: {', '.join(COMMANDS)}")
        sys.exit(1)

    fn, usage = COMMANDS[cmd]
    try:
        fn(sys.argv[2:])
    except (IndexError, ValueError) as e:
        print(f"Usage: python3 dates.py {cmd} {usage}")
        if str(e):
            print(f"Error: {e}")
        sys.exit(1)
