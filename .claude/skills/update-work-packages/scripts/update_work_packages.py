#!/usr/bin/env python3
"""Update OpenProject work packages from a JSON input file.

Reads an array of update objects, fetches the current lockVersion for each,
then PATCHes only the fields specified. Supports all standard fields,
project-specific custom fields, and work package relations (dependencies).

Usage:
    python3 update_work_packages.py --input <updates.json>

Input JSON format (array of update objects):
    [
        {
            "id": 59484,                          (required)
            "subject": "New title",               (optional)
            "description": "Markdown text",       (optional)
            "startDate": "2026-04-10",            (optional)
            "dueDate": "2026-04-30",              (optional)
            "estimatedHours": 8,                  (optional, numeric)
            "assigneeId": 64,                     (optional)
            "responsibleId": 118,                 (optional)
            "statusId": 7,                        (optional)
            "comment": "Plain text comment",      (optional)
            "fields": { "customField1": "OPS-012" },           (optional)
            "links": { "customField3": "/api/v3/custom_options/1" },  (optional)
            "relations": [                         (optional)
                {"type": "blocked_by", "targetId": 60352},
                {"type": "blocks",     "targetId": 12345},
                {"type": "relates",    "targetId": 99999}
            ]
        }
    ]

Relation types: blocks, blocked_by, relates, precedes, follows,
                duplicates, duplicated_by

A work package can have ONLY a comment or relations (no field changes).

Output JSON (stdout):
    {
        "updated": [
            {
                "id": 59484,
                "subject": "...",
                "type": "Task",
                "assignee": "Md. Abdullah Al Noman",
                "startDate": "2026-04-09",
                "dueDate": "2026-04-09",
                "work": "4h",
                "status": "In progress",
                "link": "http://...",
                "changed_fields": ["assignee", "status", "relation:blocked_by:#60352"]
            }
        ],
        "total": 1,
        "errors": []
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


def patch_json(url, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


def post_comment(wp_id, comment_text):
    """Post a comment (activity) on a work package. Returns the activity ID."""
    url = f"{BASE_URL}/work_packages/{wp_id}/activities"
    payload = json.dumps({"comment": {"raw": comment_text}}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=_headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            return data.get("id")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


# Maps user-friendly relation type names to OpenProject API type strings.
_RELATION_TYPE_MAP = {
    "blocks":        "blocks",
    "blocked_by":    "blocked",
    "blocked":       "blocked",
    "relates":       "relates",
    "precedes":      "precedes",
    "follows":       "follows",
    "duplicates":    "duplicates",
    "duplicated_by": "duplicated",
    "duplicated":    "duplicated",
}


def post_relation(wp_id, relation_type, target_id):
    """Create a relation from wp_id to target_id via the Relations API.

    Returns the normalised relation type string as reported by the API.
    Raises RuntimeError on failure.
    """
    api_type = _RELATION_TYPE_MAP.get(relation_type)
    if api_type is None:
        raise RuntimeError(
            f"Unknown relation type '{relation_type}'. "
            f"Valid types: {', '.join(_RELATION_TYPE_MAP)}"
        )
    url = f"{BASE_URL}/work_packages/{wp_id}/relations"
    payload = json.dumps({
        "_type": "Relation",
        "type": api_type,
        "_links": {
            "from": {"href": f"/api/v3/work_packages/{wp_id}"},
            "to":   {"href": f"/api/v3/work_packages/{target_id}"},
        },
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=_headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            return data.get("type", api_type)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------

def hours_to_iso(h):
    """Convert numeric hours to ISO 8601 duration string. 8.5 → 'PT8H30M'."""
    hours = int(h)
    minutes = round((h - hours) * 60)
    if minutes:
        return f"PT{hours}H{minutes}M"
    return f"PT{hours}H"


def iso_to_hours(duration):
    """Convert ISO 8601 duration to human-readable string. 'PT4H30M' → '4.5h'."""
    if not duration:
        return None
    h = re.search(r"(\d+)H", duration)
    m = re.search(r"(\d+)M", duration)
    total = (int(h.group(1)) if h else 0) + (int(m.group(1)) / 60 if m else 0)
    return f"{int(total)}h" if total == int(total) else f"{total:.1f}h"


# ---------------------------------------------------------------------------
# Build PATCH body
# ---------------------------------------------------------------------------

def build_patch_body(item, lock_version):
    """Build the PATCH request body from an update item dict."""
    body = {"lockVersion": lock_version, "_links": {}}
    changed = []

    if "subject" in item:
        body["subject"] = item["subject"]
        changed.append("subject")

    if "description" in item:
        body["description"] = {"format": "markdown", "raw": item["description"]}
        changed.append("description")

    if "startDate" in item:
        body["startDate"] = item["startDate"]
        changed.append("startDate")

    if "dueDate" in item:
        body["dueDate"] = item["dueDate"]
        changed.append("dueDate")

    if "estimatedHours" in item:
        h = item["estimatedHours"]
        body["estimatedTime"] = hours_to_iso(h) if isinstance(h, (int, float)) else h
        changed.append("work")

    if "assigneeId" in item:
        aid = item["assigneeId"]
        body["_links"]["assignee"] = {"href": None if aid is None else f"/api/v3/users/{aid}"}
        changed.append("assignee")

    if "responsibleId" in item:
        rid = item["responsibleId"]
        body["_links"]["responsible"] = {"href": None if rid is None else f"/api/v3/users/{rid}"}
        changed.append("responsible")

    if "parentId" in item:
        pid = item["parentId"]
        if pid is None:
            body["_links"]["parent"] = {"href": None}
        else:
            body["_links"]["parent"] = {"href": f"/api/v3/work_packages/{pid}"}
        changed.append("parent")

    if "projectId" in item:
        body["_links"]["project"] = {"href": f"/api/v3/projects/{item['projectId']}"}
        changed.append("project")

    if "statusId" in item:
        body["_links"]["status"] = {"href": f"/api/v3/statuses/{item['statusId']}"}
        changed.append("status")

    # Plain-value custom fields (text, integer, float)
    for field_key, value in item.get("fields", {}).items():
        body[field_key] = value
        changed.append(field_key)

    # Link-type custom fields (list options)
    for field_key, href in item.get("links", {}).items():
        body["_links"][field_key] = {"href": href}
        changed.append(field_key)

    if not body["_links"]:
        del body["_links"]

    return body, changed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Update OpenProject work packages from a JSON input file"
    )
    parser.add_argument("--input", required=True, help="Path to the updates JSON file")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(items, list):
        print("Error: input JSON must be an array of update objects", file=sys.stderr)
        sys.exit(1)

    updated = []
    errors = []

    for item in items:
        wp_id = item.get("id")
        if not wp_id:
            errors.append({"id": None, "error": "Missing 'id' field"})
            continue

        # Fetch current WP to get lockVersion
        try:
            current = fetch_json(f"{BASE_URL}/work_packages/{wp_id}")
        except RuntimeError as e:
            errors.append({"id": wp_id, "error": f"Failed to fetch WP: {e}"})
            continue

        lock_version = current.get("lockVersion")
        if lock_version is None:
            errors.append({"id": wp_id, "error": "Could not read lockVersion from WP"})
            continue

        # Ensure there is something to do
        comment_text = item.get("comment")
        has_work = (
            comment_text
            or item.get("relations")
            or any(k in item for k in ("subject", "description", "startDate", "dueDate",
                                       "estimatedHours", "assigneeId", "responsibleId",
                                       "parentId", "statusId"))
            or item.get("fields")
            or item.get("links")
        )
        if not has_work:
            errors.append({"id": wp_id, "error": "No fields to update and no comment or relations to post"})
            continue

        # Build and apply PATCH (if there are field changes)
        body, changed = build_patch_body(item, lock_version)

        if changed:
            try:
                result = patch_json(f"{BASE_URL}/work_packages/{wp_id}", body)
            except RuntimeError as e:
                errors.append({"id": wp_id, "error": str(e)})
                continue
        else:
            # No field changes — use the fetched current state
            result = current

        # Post comment if provided (after PATCH so the comment appears after the change)
        if comment_text:
            try:
                post_comment(wp_id, comment_text)
                changed.append("comment")
            except RuntimeError as e:
                errors.append({"id": wp_id, "error": f"Updated fields OK but comment failed: {e}"})

        # Create relations if provided
        for rel in item.get("relations", []):
            rel_type = rel.get("type")
            target_id = rel.get("targetId")
            if not rel_type or not target_id:
                errors.append({"id": wp_id, "error": f"Relation missing 'type' or 'targetId': {rel}"})
                continue
            try:
                actual_type = post_relation(wp_id, rel_type, target_id)
                changed.append(f"relation:{rel_type}:#{target_id}")
            except RuntimeError as e:
                errors.append({"id": wp_id, "error": f"Relation ({rel_type} → #{target_id}) failed: {e}"})

        if not changed:
            errors.append({"id": wp_id, "error": "Nothing was updated (all changes failed or were empty)"})
            continue

        links = result.get("_links", {})
        updated.append({
            "id": result.get("id", wp_id),
            "subject": result.get("subject", ""),
            "type": links.get("type", {}).get("title", "-"),
            "assignee": links.get("assignee", {}).get("title") or None,
            "startDate": result.get("startDate") or None,
            "dueDate": result.get("dueDate") or None,
            "work": iso_to_hours(result.get("estimatedTime")),
            "status": links.get("status", {}).get("title", "-"),
            "link": f"{WP_BASE}/{wp_id}",
            "changed_fields": changed,
        })

    print(json.dumps({"updated": updated, "total": len(updated), "errors": errors}, indent=2))


if __name__ == "__main__":
    main()
