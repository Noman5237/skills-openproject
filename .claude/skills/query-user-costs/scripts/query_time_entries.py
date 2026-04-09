#!/usr/bin/env python3
"""Fetch time entries for a user in a date range, with work package status.

Usage:
    python3 query_time_entries.py <user_id> <start_date> <end_date>

Dates in YYYY-MM-DD format.
Outputs JSON: {total_entries, total_hours, user, entries: [{date, project, task, taskId, status, startDate, dueDate, work, totalSpent, updatedAt, hours, comment}]}
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import get_api_config

_OP_BASE, BASE_URL, _WP_BASE, headers = get_api_config()

if len(sys.argv) < 4:
    print(f"Usage: {sys.argv[0]} <user_id> <start_date> <end_date>", file=sys.stderr)
    sys.exit(1)

user_id, start_date, end_date = sys.argv[1], sys.argv[2], sys.argv[3]


def parse_duration(iso_duration):
    """Convert ISO 8601 duration (e.g. PT2H30M) to decimal hours."""
    if not iso_duration:
        return 0.0
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not m:
        return 0.0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    return hours + minutes / 60


def fetch_json(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


_C = (",", ":")  # compact JSON separators required by OpenProject filter params


def fetch_time_entries():
    filters = json.dumps([
        {"user": {"operator": "=", "values": [user_id]}},
        {"spentOn": {"operator": "<>d", "values": [start_date, end_date]}},
    ], separators=_C)
    sort_by = json.dumps([["spentOn", "asc"]], separators=_C)
    all_entries = []
    offset = 1
    while True:
        params = urllib.parse.urlencode({
            "filters": filters,
            "sortBy": sort_by,
            "pageSize": 100,
            "offset": offset,
        })
        data = fetch_json(f"{BASE_URL}/time_entries?{params}")
        elements = data.get("_embedded", {}).get("elements", [])
        all_entries.extend(elements)
        total = data.get("total", 0)
        if offset * 100 >= total:
            break
        offset += 1
    return all_entries


def fetch_wp_details(wp_ids):
    """Batch-fetch work package details (status, dates, work, spent) by ID."""
    if not wp_ids:
        return {}
    filters = json.dumps([{"id": {"operator": "=", "values": list(wp_ids)}}], separators=_C)
    params = urllib.parse.urlencode({"filters": filters, "pageSize": 500})
    data = fetch_json(f"{BASE_URL}/work_packages?{params}")
    result = {}
    for el in data.get("_embedded", {}).get("elements", []):
        wp_id = str(el["id"])
        # updatedAt is used as proxy for when the WP was last transitioned (e.g. closed)
        updated_at = (el.get("updatedAt") or "")[:10]  # keep only YYYY-MM-DD
        result[wp_id] = {
            "status": el.get("_links", {}).get("status", {}).get("title", "-"),
            "startDate": el.get("startDate") or "-",
            "dueDate": el.get("dueDate") or "-",
            "work": parse_duration(el.get("estimatedTime")),
            "spent": parse_duration(el.get("spentTime")),
            "updatedAt": updated_at,
        }
    return result


def fetch_user_name():
    data = fetch_json(f"{BASE_URL}/users/{user_id}")
    return data.get("name", user_id)


entries = fetch_time_entries()

# Collect unique WP IDs for status batch-fetch
wp_ids = set()
for e in entries:
    wp_href = e.get("_links", {}).get("workPackage", {}).get("href", "")
    if wp_href:
        wp_ids.add(wp_href.split("/")[-1])

wp_details = fetch_wp_details(wp_ids)
user_name = fetch_user_name()

result = []
for e in entries:
    links = e.get("_links", {})
    wp_href = links.get("workPackage", {}).get("href", "")
    wp_id = wp_href.split("/")[-1] if wp_href else None
    hours = parse_duration(e.get("hours"))
    wp = wp_details.get(wp_id, {}) if wp_id else {}
    result.append({
        "date": e.get("spentOn"),
        "project": links.get("project", {}).get("title", "-"),
        "task": links.get("workPackage", {}).get("title", "-"),
        "taskId": wp_id,
        "status": wp.get("status", "-"),
        "startDate": wp.get("startDate", "-"),
        "dueDate": wp.get("dueDate", "-"),
        "work": wp.get("work", 0.0),
        "totalSpent": wp.get("spent", 0.0),
        "updatedAt": wp.get("updatedAt", "-"),
        "hours": round(hours, 2),
        "comment": (e.get("comment") or {}).get("raw", "") or "",
    })

total_hours = round(sum(r["hours"] for r in result), 2)
print(json.dumps({
    "user": user_name,
    "start": start_date,
    "end": end_date,
    "total_entries": len(result),
    "total_hours": total_hours,
    "entries": result,
}))
