#!/usr/bin/env python3
"""Create OpenProject work packages from a hierarchy JSON file.

Reads a JSON file describing one or more work packages (optionally nested),
creates them in depth-first order so parents exist before children, and
automatically sets the parent link on each child.

Usage:
    python3 create_work_packages.py --input <hierarchy.json>

Input JSON format:
    {
        "projectId": 5,
        "items": [
            {
                "subject": "Epic: My Feature Set",
                "typeId": 5,
                "startDate": "2026-04-15",          (optional)
                "dueDate": "2026-04-30",            (optional)
                "estimatedHours": 80,               (optional, number)
                "assigneeId": 64,                   (optional)
                "statusId": 1,                      (optional, defaults to 1 = New)
                "fields": {                         (optional)
                    "customField1": "1.0"           plain-value custom fields (text/int/float)
                },
                "links": {                          (optional)
                    "customField3": "/api/v3/custom_options/5"   link-type custom fields
                },
                "children": [...]                   (optional, same structure, nested)
            }
        ]
    }

Output JSON (stdout):
    {
        "created": [
            {
                "id": 1234,
                "subject": "Epic: My Feature Set",
                "type": "Epic",
                "assignee": "Md. Abdullah Al Noman",
                "startDate": "2026-04-10",
                "dueDate": "2026-04-10",
                "work": "8h",
                "status": "New",
                "link": "http://project.global.fintech23.xyz/work_packages/1234",
                "children": [...]
            }
        ],
        "total": 3,
        "errors": [
            {"subject": "...", "error": "HTTP 422: ..."}
        ]
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


def iso_to_hours(duration):
    """Convert ISO 8601 duration to human-readable string. 'PT4H30M' → '4.5h'."""
    if not duration:
        return None
    h = re.search(r"(\d+)H", duration)
    m = re.search(r"(\d+)M", duration)
    total = (int(h.group(1)) if h else 0) + (int(m.group(1)) / 60 if m else 0)
    return f"{int(total)}h" if total == int(total) else f"{total:.1f}h"


def post_work_package(body):
    """POST to /api/v3/work_packages and return the parsed response."""
    url = f"{BASE_URL}/work_packages"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {error_body}")


def build_request_body(item, project_id, parent_id=None):
    """Construct the API request body from a normalized item dict."""
    body = {
        "subject": item["subject"],
        "_links": {
            "project": {"href": f"/api/v3/projects/{project_id}"},
            "type": {"href": f"/api/v3/types/{item['typeId']}"},
        },
    }

    if "startDate" in item:
        body["startDate"] = item["startDate"]
    if "dueDate" in item:
        body["dueDate"] = item["dueDate"]
    if "estimatedHours" in item:
        h = item["estimatedHours"]
        # Convert numeric hours to ISO 8601 duration string
        if isinstance(h, (int, float)):
            hours = int(h)
            minutes = round((h - hours) * 60)
            body["estimatedTime"] = f"PT{hours}H{minutes}M" if minutes else f"PT{hours}H"
        else:
            body["estimatedTime"] = h  # already a string like "PT8H"

    if "assigneeId" in item and item["assigneeId"]:
        body["_links"]["assignee"] = {"href": f"/api/v3/users/{item['assigneeId']}"}
    if "statusId" in item:
        body["_links"]["status"] = {"href": f"/api/v3/statuses/{item['statusId']}"}
    if parent_id is not None:
        body["_links"]["parent"] = {"href": f"/api/v3/work_packages/{parent_id}"}

    # Plain-value custom fields go directly in the body
    for field_key, value in item.get("fields", {}).items():
        body[field_key] = value

    # Link-type custom fields (e.g. list options) go in _links
    for field_key, href in item.get("links", {}).items():
        body["_links"][field_key] = {"href": href}

    return body


def create_item_recursive(item, project_id, parent_id, errors):
    """Create one work package and recursively create its children."""
    body = build_request_body(item, project_id, parent_id)
    try:
        result = post_work_package(body)
    except RuntimeError as e:
        errors.append({"subject": item.get("subject", "(unknown)"), "error": str(e)})
        return None

    wp_id = result["id"]
    links = result.get("_links", {})
    type_title = links.get("type", {}).get("title", f"type/{item.get('typeId', '?')}")

    created_node = {
        "id": wp_id,
        "subject": result.get("subject", item["subject"]),
        "type": type_title,
        "assignee": links.get("assignee", {}).get("title") or None,
        "startDate": result.get("startDate") or None,
        "dueDate": result.get("dueDate") or None,
        "work": iso_to_hours(result.get("estimatedTime")),
        "status": links.get("status", {}).get("title", "New"),
        "link": f"{WP_BASE}/{wp_id}",
        "children": [],
    }

    for child in item.get("children", []):
        child_result = create_item_recursive(child, project_id, wp_id, errors)
        if child_result is not None:
            created_node["children"].append(child_result)

    return created_node


def count_nodes(node):
    """Count total nodes in a created-items tree."""
    return 1 + sum(count_nodes(c) for c in node.get("children", []))


def main():
    parser = argparse.ArgumentParser(
        description="Create OpenProject work packages from a hierarchy JSON file"
    )
    parser.add_argument("--input", required=True, help="Path to the hierarchy JSON file")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    project_id = data.get("projectId")
    if not project_id:
        print("Error: input JSON must have a 'projectId' field", file=sys.stderr)
        sys.exit(1)

    items = data.get("items", [])
    if not items:
        print("Warning: no items to create", file=sys.stderr)
        print(json.dumps({"created": [], "total": 0, "errors": []}))
        return

    created = []
    errors = []

    for item in items:
        top_level_parent = item.pop("parentId", None)
        result = create_item_recursive(item, project_id, top_level_parent, errors)
        if result is not None:
            created.append(result)

    total = sum(count_nodes(c) for c in created)

    output = {"created": created, "total": total, "errors": errors}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
