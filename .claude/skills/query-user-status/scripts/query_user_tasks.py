#!/usr/bin/env python3
"""Query open tasks assigned to a user across all OpenProject projects.

Outputs JSON with task details including project name, parent hierarchy, dates, and hours.

Usage:
    python3 query_user_tasks.py <user_id>
    python3 query_user_tasks.py <user_id> --status 1,6,7

Default statuses: 1 (New), 6 (To Do), 7 (In progress), 13 (On hold)
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import get_api_config

_OP_BASE, BASE_URL, WP_LINK, _api_headers = get_api_config()

DEFAULT_STATUSES = ["1", "6", "7", "13"]

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <user_id> [--status 1,6,7]", file=sys.stderr)
    sys.exit(1)

user_id = sys.argv[1]

# Parse optional flags
statuses = DEFAULT_STATUSES
for i, arg in enumerate(sys.argv[2:], start=2):
    if arg == "--status" and i + 1 < len(sys.argv):
        statuses = sys.argv[i + 1].split(",")
        break

headers = _api_headers


# ---------------------------------------------------------------------------
# Workday calendar — reads same config as workdays and assign-work-packages
# ---------------------------------------------------------------------------

def _load_config():
    settings_path = os.path.join(os.getcwd(), ".memory", "settings", "workweek.json")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            cfg = json.load(f)
        return frozenset(cfg.get("weekend", [4, 5])), int(cfg.get("hours_per_day", 8))
    return frozenset([4, 5]), 8  # Bangladesh defaults: Fri=4 Sat=5, 8h/day


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


def count_working_days(start: date, end: date) -> int:
    """Count working days in [start, end] inclusive."""
    count = 0
    current = start
    while current <= end:
        if is_workday(current):
            count += 1
        current += timedelta(days=1)
    return count


def parse_duration(iso_duration):
    """Convert ISO 8601 duration (e.g. PT2H30M) to decimal hours string."""
    if not iso_duration:
        return "-"
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not m:
        return "-"
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    total = hours + minutes / 60
    if total == 0:
        return "-"
    return f"{total:.1f}h"


def parse_duration_hours(iso_duration):
    """Convert ISO 8601 duration to decimal hours (float). Returns 0.0 if none."""
    if not iso_duration:
        return 0.0
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not m:
        return 0.0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    return hours + minutes / 60


def fetch_page(offset):
    filters = json.dumps([
        {"assignee": {"operator": "=", "values": [user_id]}},
        {"status": {"operator": "=", "values": statuses}},
        {"type": {"operator": "=", "values": ["1"]}},   # Tasks only
    ])
    sort_by = json.dumps([["project", "asc"], ["updatedAt", "desc"]])
    params = urllib.parse.urlencode({
        "filters": filters,
        "sortBy": sort_by,
        "pageSize": 100,
        "offset": offset,
    })
    url = f"{BASE_URL}/work_packages?{params}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def extract_task(el):
    links = el.get("_links", {})
    parent_link = links.get("parent", {})
    ancestors = links.get("ancestors", [])

    parent_hierarchy = []
    for anc in ancestors:
        title = anc.get("title", "")
        if title:
            parent_hierarchy.append(title)

    work_hours = parse_duration_hours(el.get("estimatedTime"))
    remaining_raw = el.get("remainingTime")
    # Use API-provided remainingTime; fall back to estimatedTime when no time has been logged yet
    remaining_hours = parse_duration_hours(remaining_raw) if remaining_raw else work_hours

    return {
        "id": el.get("id"),
        "subject": el.get("subject"),
        "type": links.get("type", {}).get("title"),
        "status": links.get("status", {}).get("title"),
        "project": links.get("project", {}).get("title"),
        "assignee": links.get("assignee", {}).get("title", "-"),
        "parent": parent_link.get("title") if parent_link.get("href") else None,
        "ancestors": parent_hierarchy if parent_hierarchy else None,
        "startDate": el.get("startDate") or "-",
        "dueDate": el.get("dueDate") or "-",
        "work": parse_duration(el.get("estimatedTime")),
        "workHours": work_hours,
        "spent": parse_duration(el.get("spentTime")),
        "remainingHours": remaining_hours,
        "link": f"{WP_LINK}/{el.get('id')}",
    }


# Fetch all pages
all_tasks = []
offset = 1
while True:
    data = fetch_page(offset)
    elements = data.get("_embedded", {}).get("elements", [])
    all_tasks.extend(extract_task(el) for el in elements)
    total = data.get("total", 0)
    if offset * 100 >= total:
        break
    offset += 1

# Flag Tasks in "New" that are fully scheduled (start + due + work all set)
for task in all_tasks:
    if (task["status"] == "New"
            and task["startDate"] != "-"
            and task["dueDate"] != "-"
            and task["workHours"] > 0):
        task["scheduledInNew"] = True

# ---------------------------------------------------------------------------
# Overload detection: cumulative feasibility check
# ---------------------------------------------------------------------------
today = date.today()

# Collect eligible tasks: have dueDate, remaining > 0, dueDate >= today
eligible = []
for task in all_tasks:
    remaining = task.get("remainingHours", 0.0)
    due_str = task.get("dueDate")
    if not due_str or due_str == "-" or remaining <= 0:
        continue
    due_d = date.fromisoformat(due_str)
    if due_d < today:
        continue

    start_str = task.get("startDate")
    has_start = start_str and start_str != "-"
    if has_start:
        start_d = date.fromisoformat(start_str)
        effective_start = start_d if start_d > today else today
    else:
        effective_start = today

    # Per-task feasibility: can this task alone be finished in its window?
    if effective_start > due_d:
        feasible = False
        task_available = 0.0
    else:
        task_available = count_working_days(effective_start, due_d) * _HOURS_PER_DAY
        feasible = remaining <= task_available

    eligible.append({
        "id": task["id"],
        "subject": task["subject"],
        "type": task["type"],
        "status": task["status"],
        "parent": task["parent"],
        "startDate": task["startDate"],
        "dueDate": task["dueDate"],
        "work": task["work"],
        "spent": task["spent"],
        "remaining": round(remaining, 2),
        "effectiveStart": effective_start.isoformat(),
        "taskAvailable": round(task_available, 1),
        "feasible": feasible,
        "link": task["link"],
    })

# Sort by dueDate ascending for cumulative check
eligible.sort(key=lambda t: t["dueDate"])

# Cumulative overload: walk through due dates, accumulate remaining hours
overloaded_dates = []
cumulative_remaining = 0.0
processed_idx = 0

# Group by unique dueDate
due_dates_seen: dict = {}  # dueDate -> list of task entries
for entry in eligible:
    due_dates_seen.setdefault(entry["dueDate"], []).append(entry)

for due_str in sorted(due_dates_seen.keys()):
    tasks_at_date = due_dates_seen[due_str]
    cumulative_remaining += sum(t["remaining"] for t in tasks_at_date)
    due_d = date.fromisoformat(due_str)
    available = count_working_days(today, due_d) * _HOURS_PER_DAY

    if cumulative_remaining > available:
        # Collect ALL tasks due <= this date for the full picture
        all_tasks_by_now = [t for t in eligible if t["dueDate"] <= due_str]
        overloaded_dates.append({
            "date": due_str,
            "cumulativeRemaining": round(cumulative_remaining, 1),
            "availableHours": round(available, 1),
            "deficit": round(cumulative_remaining - available, 1),
            "tasks": all_tasks_by_now,
        })

print(json.dumps({"total": len(all_tasks), "tasks": all_tasks, "overloaded_dates": overloaded_dates}))
