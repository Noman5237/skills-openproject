#!/usr/bin/env python3
"""Log time entries to OpenProject work packages.

Usage:
    python3 log_time.py --input <entries.json>

Input JSON format (array):
    [
        {
            "workPackageId": 59791,       (required)
            "hours": "PT2H",             (required, ISO 8601)
            "spentOn": "2026-04-09",     (required, YYYY-MM-DD)
            "comment": "description",     (optional)
            "activityId": 3,              (optional, default by project)
            "userId": 64                  (optional, default authenticated user)
        }
    ]

Output JSON (stdout):
    {
        "logged": [...],
        "total": N,
        "totalHours": "X.Xh",
        "errors": [...]
    }
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import get_api_config

_OP_BASE, BASE_URL, WP_BASE, _headers = get_api_config()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch_json(url):
    req = urllib.request.Request(url, headers=_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


def post_json(url, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------

def iso_to_hours(duration):
    """Convert ISO 8601 duration to human-readable string. 'PT4H30M' → '4.5h'."""
    if not duration:
        return None
    h = re.search(r"(\d+)H", duration)
    m = re.search(r"(\d+)M", duration)
    total = (int(h.group(1)) if h else 0) + (int(m.group(1)) / 60 if m else 0)
    return f"{int(total)}h" if total == int(total) else f"{total:.1f}h"


def iso_to_decimal(duration):
    """Convert ISO 8601 duration to decimal hours. 'PT2H30M' → 2.5."""
    if not duration:
        return 0.0
    h = re.search(r"(\d+)H", duration)
    m = re.search(r"(\d+)M", duration)
    return (int(h.group(1)) if h else 0) + (int(m.group(1)) / 60 if m else 0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Log time entries to OpenProject")
    parser.add_argument("--input", required=True, help="Path to the time entries JSON file")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(items, list):
        print("Error: input JSON must be an array of time entry objects", file=sys.stderr)
        sys.exit(1)

    logged = []
    errors = []
    total_decimal = 0.0

    for item in items:
        wp_id = item.get("workPackageId")
        hours = item.get("hours")
        spent_on = item.get("spentOn")

        if not wp_id or not hours or not spent_on:
            errors.append({
                "workPackageId": wp_id,
                "error": "Missing required field (workPackageId, hours, or spentOn)",
            })
            continue

        # Build POST body
        body = {
            "_links": {
                "workPackage": {"href": f"/api/v3/work_packages/{wp_id}"},
            },
            "hours": hours,
            "spentOn": spent_on,
        }

        # Optional user
        user_id = item.get("userId")
        if user_id:
            body["_links"]["user"] = {"href": f"/api/v3/users/{user_id}"}

        # Optional activity
        activity_id = item.get("activityId")
        if activity_id:
            body["_links"]["activity"] = {"href": f"/api/v3/time_entries/activities/{activity_id}"}

        # Optional comment
        comment = item.get("comment")
        if comment:
            body["comment"] = {"raw": comment}

        # POST the time entry
        try:
            result = post_json(f"{BASE_URL}/time_entries", body)
        except RuntimeError as e:
            errors.append({"workPackageId": wp_id, "error": str(e)})
            continue

        links = result.get("_links", {})
        result_hours = result.get("hours", "")
        decimal_hours = iso_to_decimal(result_hours)
        total_decimal += decimal_hours

        logged.append({
            "id": result.get("id"),
            "workPackageId": wp_id,
            "subject": links.get("workPackage", {}).get("title", ""),
            "project": links.get("project", {}).get("title", ""),
            "user": links.get("user", {}).get("title", ""),
            "hours": iso_to_hours(result_hours),
            "spentOn": result.get("spentOn", spent_on),
            "comment": result.get("comment", {}).get("raw", "") or "",
            "activity": links.get("activity", {}).get("title", "—"),
            "link": f"{WP_BASE}/{wp_id}",
        })

    total_str = f"{int(total_decimal)}h" if total_decimal == int(total_decimal) else f"{total_decimal:.1f}h"

    print(json.dumps({
        "logged": logged,
        "total": len(logged),
        "totalHours": total_str,
        "errors": errors,
    }, indent=2))


if __name__ == "__main__":
    main()
