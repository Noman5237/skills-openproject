#!/usr/bin/env python3
"""Delete OpenProject work packages from a JSON input file.

Reads an array of work package IDs and DELETEs each one via the API.
Order matters — list children before parents to avoid cascading issues.

Usage:
    python3 delete_work_packages.py --input <ids.json>

Input JSON format (array of IDs):
    [59488, 59487]

Output JSON (stdout):
    {
        "deleted": [
            {"id": 59488, "subject": "Dummy Task", "type": "Task", "status": 204},
            {"id": 59487, "subject": "Dummy User Story", "type": "User story", "status": 204}
        ],
        "total": 2,
        "errors": []
    }
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import get_api_config

_OP_BASE, BASE_URL, WP_BASE, _headers = get_api_config()


def fetch_json(url):
    req = urllib.request.Request(url, headers=_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


def delete_wp(url):
    req = urllib.request.Request(url, headers=_headers, method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


def main():
    parser = argparse.ArgumentParser(
        description="Delete OpenProject work packages from a JSON input file"
    )
    parser.add_argument("--input", required=True, help="Path to the JSON file with WP IDs")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            ids = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(ids, list):
        print("Error: input JSON must be an array of work package IDs", file=sys.stderr)
        sys.exit(1)

    deleted = []
    errors = []

    for wp_id in ids:
        if not isinstance(wp_id, int):
            errors.append({"id": wp_id, "error": "ID must be an integer"})
            continue

        # Fetch WP metadata before deleting (for reporting)
        try:
            wp = fetch_json(f"{BASE_URL}/work_packages/{wp_id}")
            subject = wp.get("subject", "")
            wp_type = wp.get("_links", {}).get("type", {}).get("title", "-")
        except RuntimeError as e:
            errors.append({"id": wp_id, "error": f"Failed to fetch WP: {e}"})
            continue

        # Delete
        try:
            status = delete_wp(f"{BASE_URL}/work_packages/{wp_id}")
            deleted.append({
                "id": wp_id,
                "subject": subject,
                "type": wp_type,
                "link": f"{WP_BASE}/{wp_id}",
                "status": status,
            })
        except RuntimeError as e:
            errors.append({"id": wp_id, "error": str(e)})

    print(json.dumps({"deleted": deleted, "total": len(deleted), "errors": errors}, indent=2))


if __name__ == "__main__":
    main()
