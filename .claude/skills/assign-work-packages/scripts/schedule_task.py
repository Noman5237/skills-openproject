#!/usr/bin/env python3
"""
schedule_task.py — Compute start/due dates for a new task based on assignee workload.

Run from the project root so it can find .memory/holidays/ and .memory/settings/.

Usage:
  python3 schedule_task.py --assignee-id 64 --hours 4 [--start 2026-04-09] [--project 94]

Output JSON:
  {
    "startDate": "2026-04-10",
    "dueDate": "2026-04-10",
    "baselineTask": {"id": 59488, "subject": "...", "dueDate": "2026-04-09"},
    "existingTasks": [...],
    "conflicts": [{"date": "2026-04-10", "totalHours": 12.0, "tasks": ["Task A", "new task"]}]
  }
"""

import argparse
import base64
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Workday calendar — mirrors workdays/scripts/dates.py, reads same config files
# ---------------------------------------------------------------------------

def _load_config():
    settings_path = os.path.join(os.getcwd(), ".memory", "settings", "workweek.json")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            cfg = json.load(f)
        return frozenset(cfg.get("weekend", [4, 5])), int(cfg.get("hours_per_day", 8))
    return frozenset([4, 5]), 8  # Bangladesh defaults: Fri=4 Sat=5 weekend, 8h/day


_WEEKEND, _HOURS_PER_DAY = _load_config()
_holiday_cache: dict = {}


def _load_holidays(year: int) -> set:
    path = os.path.join(os.getcwd(), ".memory", "holidays", f"{year}.json")
    if os.path.exists(path):
        with open(path) as f:
            return {h["date"] for h in json.load(f)}
    return set()


def _holidays(year: int) -> set:
    if year not in _holiday_cache:
        _holiday_cache[year] = _load_holidays(year)
    return _holiday_cache[year]


def is_workday(d: date) -> bool:
    return d.weekday() not in _WEEKEND and d.isoformat() not in _holidays(d.year)


def add_workdays(start: date, n: int) -> date:
    current = start
    added = 0
    while added < n:
        current += timedelta(days=1)
        if is_workday(current):
            added += 1
    return current


def workdays_in_range(start: date, end: date) -> list:
    days = []
    current = start
    while current <= end:
        if is_workday(current):
            days.append(current)
        current += timedelta(days=1)
    return days


def compute_due(start: date, hours: float) -> date:
    """Compute due date: start day counts as day 1, add extra days as needed."""
    if hours <= 0:
        return start
    days_needed = math.ceil(hours / _HOURS_PER_DAY)
    extra = days_needed - 1
    return add_workdays(start, extra) if extra > 0 else start


# ---------------------------------------------------------------------------
# OpenProject API
# ---------------------------------------------------------------------------

_OP_BASE = os.environ.get("OPENPROJECT_BASE_URL", "http://project.global.fintech23.xyz").rstrip("/")


def _api_key() -> str:
    key = os.environ.get("OPENPROJECT_API_KEY", "")
    if not key:
        print("Error: OPENPROJECT_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    return key


def _api_get(path: str) -> dict:
    key = _api_key()
    creds = base64.b64encode(f"apikey:{key}".encode()).decode()
    req = urllib.request.Request(f"{_OP_BASE}{path}", headers={"Authorization": f"Basic {creds}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _parse_iso_hours(duration: str) -> float:
    """Convert ISO 8601 duration (PT8H, PT4H30M) to decimal hours."""
    h = re.search(r"(\d+)H", duration or "")
    m = re.search(r"(\d+)M", duration or "")
    return (int(h.group(1)) if h else 0) + (int(m.group(1)) / 60 if m else 0)


def fetch_tasks(assignee_id: int, project_id: int | None) -> list:
    """Fetch all open Tasks assigned to this user."""
    filters = [
        {"assignee": {"operator": "=", "values": [str(assignee_id)]}},
        {"type": {"operator": "=", "values": ["1"]}},   # Task
        {"status": {"operator": "o", "values": []}},    # open
    ]
    if project_id:
        filters.append({"project": {"operator": "=", "values": [str(project_id)]}})

    encoded = urllib.parse.quote(json.dumps(filters))
    items = []
    page_size = 100
    offset = 1

    while True:
        data = _api_get(f"/api/v3/work_packages?filters={encoded}&pageSize={page_size}&offset={offset}")
        elements = data.get("_embedded", {}).get("elements", [])
        for e in elements:
            hours = _parse_iso_hours(e.get("estimatedTime")) if e.get("estimatedTime") else None
            remaining_raw = e.get("remainingTime")
            remaining = _parse_iso_hours(remaining_raw) if remaining_raw else (hours if hours is not None else None)
            items.append({
                "id": e["id"],
                "subject": e["subject"],
                "startDate": e.get("startDate"),
                "dueDate": e.get("dueDate"),
                "hours": hours,
                "remaining": remaining,
                "link": f"{_OP_BASE}/work_packages/{e['id']}",
            })
        total = data.get("total", 0)
        if offset * page_size >= total:
            break
        offset += 1

    return items


# ---------------------------------------------------------------------------
# Scheduling and overload detection
# ---------------------------------------------------------------------------

def detect_conflicts(existing_tasks: list, new_start: date, new_due: date, new_hours: float) -> list:
    """Return days where total assigned hours exceed the daily capacity."""
    proposed_days = workdays_in_range(new_start, new_due)
    if not proposed_days:
        return []

    # Map each workday in the proposed period to a list of (task_label, hours) contributions
    day_map: dict = {d.isoformat(): [] for d in proposed_days}

    # New task contribution — distributed evenly across its working days
    new_daily = new_hours / len(proposed_days)
    for d in proposed_days:
        day_map[d.isoformat()].append({"task": "new task", "hours": new_daily})

    # Existing tasks that overlap with the proposed period.
    # Use remaining hours (estimated - spent) so already-logged work doesn't inflate overload.
    for task in existing_tasks:
        if not task.get("startDate") or not task.get("dueDate"):
            continue
        remaining = task.get("remaining")
        if remaining is None or remaining <= 0:
            continue  # no estimate, or already fully logged
        t_start = date.fromisoformat(task["startDate"])
        t_due = date.fromisoformat(task["dueDate"])

        if t_due < new_start or t_start > new_due:
            continue  # no overlap

        t_days = workdays_in_range(t_start, t_due)
        if not t_days:
            continue
        daily = remaining / len(t_days)

        for d in t_days:
            ds = d.isoformat()
            if ds in day_map:
                day_map[ds].append({"task": task["subject"], "hours": daily})

    # Flag days that exceed daily capacity
    conflicts = []
    for ds, contributions in sorted(day_map.items()):
        total = sum(c["hours"] for c in contributions)
        if total > _HOURS_PER_DAY:
            conflicts.append({
                "date": ds,
                "totalHours": round(total, 1),
                "tasks": [c["task"] for c in contributions],
            })

    return conflicts


def main():
    parser = argparse.ArgumentParser(description="Compute task schedule for an assignee")
    parser.add_argument("--assignee-id", type=int, required=True, help="Numeric OpenProject user ID")
    parser.add_argument("--hours", type=float, required=True, help="Estimated hours for the new task")
    parser.add_argument("--start", help="Override computed start date (YYYY-MM-DD); overload check still runs")
    parser.add_argument("--project", type=int, help="Scope task search to this project ID")
    args = parser.parse_args()

    # Fetch all open tasks for the assignee
    tasks = fetch_tasks(args.assignee_id, args.project)

    # Find the task with the latest dueDate as the scheduling baseline
    scheduled = [t for t in tasks if t.get("dueDate")]
    scheduled.sort(key=lambda t: t["dueDate"])
    baseline_task = scheduled[-1] if scheduled else None

    # Compute start date
    if args.start:
        start = date.fromisoformat(args.start)
    elif baseline_task:
        last_due = date.fromisoformat(baseline_task["dueDate"])
        start = add_workdays(last_due, 1)
    else:
        # No scheduled tasks — start from today (or next workday)
        start = date.today()
        while not is_workday(start):
            start += timedelta(days=1)

    due = compute_due(start, args.hours)
    conflicts = detect_conflicts(tasks, start, due, args.hours)

    print(json.dumps({
        "startDate": start.isoformat(),
        "dueDate": due.isoformat(),
        "baselineTask": baseline_task,
        "existingTasks": tasks,
        "conflicts": conflicts,
    }, indent=2))


if __name__ == "__main__":
    main()
