#!/usr/bin/env python3
"""Get OpenProject project details by ID, optionally fetch custom field schema.

Usage:
    python3 get_project.py <project_id>
    python3 get_project.py <project_id> --schema
    python3 get_project.py <project_id> --schema --type 1,6

Examples:
    python3 get_project.py 41
    python3 get_project.py 41 --schema
    python3 get_project.py 41 --schema --type 1,4,6
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import get_api_config

_OP_BASE, BASE_URL, _WP_BASE, _headers = get_api_config()


def find_memory_root():
    """Walk up from cwd to find .memory directory."""
    d = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(d, ".memory")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def fetch_json(url):
    req = urllib.request.Request(url, headers=_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Error fetching {url}: HTTP {e.code} -- {body}", file=sys.stderr)
        sys.exit(1)


def load_global_field_keys(memory_root):
    """Load global custom field keys to exclude from per-project schemas."""
    if not memory_root:
        return set()
    path = os.path.join(memory_root, "custom-fields", "global.json")
    if not os.path.isfile(path):
        return set()
    with open(path) as f:
        data = json.load(f)
    return {cf["fieldKey"] for cf in data.get("customFields", [])}


def extract_custom_fields(schema, global_keys):
    """Extract custom fields from a work package schema, excluding global ones."""
    custom_fields = []
    for key in sorted(schema.keys()):
        if not key.startswith("customField"):
            continue
        if key in global_keys:
            continue
        field_def = schema[key]
        if not isinstance(field_def, dict):
            continue

        api_type = field_def.get("type", "")
        required = field_def.get("required", False)
        label = field_def.get("name", key)

        allowed_values = None
        notes = ""

        if api_type == "CustomOption":
            embedded = field_def.get("_embedded", {}).get("allowedValues", [])
            allowed_values = []
            for av in embedded:
                href = av.get("_links", {}).get("self", {}).get("href", "")
                option_id = href.split("/")[-1] if href else ""
                option_value = av.get("value", "")
                if option_id:
                    allowed_values.append({"id": option_id, "value": option_value})
            notes = "Use /api/v3/custom_options/{id} in _links href when setting via POST/PATCH"
            type_label = "list"
        elif api_type == "Integer":
            type_label = "integer"
        elif api_type == "Float":
            type_label = "float"
        elif api_type == "Boolean":
            type_label = "boolean"
        elif api_type == "Date":
            type_label = "date"
        else:
            type_label = "text"

        custom_fields.append({
            "fieldKey": key,
            "label": label,
            "type": type_label,
            "required": required,
            "allowedValues": allowed_values,
            "notes": notes,
        })
    return custom_fields


def write_meta(memory_root, project_info):
    """Write meta.json for the project."""
    identifier = project_info["identifier"]
    proj_dir = os.path.join(memory_root, "projects", identifier)
    os.makedirs(proj_dir, exist_ok=True)
    meta = {
        "id": project_info["id"],
        "name": project_info["name"],
        "identifier": identifier,
        "status": project_info.get("status"),
        "cachedAt": datetime.date.today().isoformat(),
    }
    with open(os.path.join(proj_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


def write_custom_fields(memory_root, identifier, project_id, type_ids, custom_fields):
    """Write custom-fields.json for the project."""
    proj_dir = os.path.join(memory_root, "projects", identifier)
    os.makedirs(proj_dir, exist_ok=True)
    data = {
        "meta": {
            "lastUpdated": datetime.date.today().isoformat(),
            "typesChecked": type_ids,
            "source": f"GET /api/v3/work_packages/schemas/{project_id}-{{type_id}}",
            "notes": "Global fields excluded -- see .memory/custom-fields/global.json",
        },
        "customFields": custom_fields,
    }
    with open(os.path.join(proj_dir, "custom-fields.json"), "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# --- CLI ---

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <project_id> [--schema] [--type TYPE_IDS]", file=sys.stderr)
    sys.exit(1)

project_id = sys.argv[1]
fetch_schema = False
type_ids = [1, 6]  # Task, User Story

i = 2
while i < len(sys.argv):
    if sys.argv[i] == "--schema":
        fetch_schema = True
        i += 1
    elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
        type_ids = [int(t) for t in sys.argv[i + 1].split(",")]
        i += 2
    else:
        i += 1

# Fetch project details
project_data = fetch_json(f"{BASE_URL}/projects/{project_id}")
status_title = project_data.get("_links", {}).get("status", {}).get("title", "")

result = {
    "id": project_data["id"],
    "name": project_data["name"],
    "identifier": project_data["identifier"],
    "description": (project_data.get("description", {}) or {}).get("raw", ""),
    "status": status_title or None,
    "public": project_data.get("public", False),
}

memory_root = find_memory_root()

# Write meta.json
if memory_root:
    write_meta(memory_root, result)

# Fetch and cache custom field schema
if fetch_schema:
    global_keys = load_global_field_keys(memory_root)
    all_custom_fields = {}

    for tid in type_ids:
        schema_url = f"{BASE_URL}/work_packages/schemas/{project_id}-{tid}"
        schema = fetch_json(schema_url)
        for cf in extract_custom_fields(schema, global_keys):
            all_custom_fields[cf["fieldKey"]] = cf

    custom_fields = sorted(all_custom_fields.values(), key=lambda c: c["fieldKey"])
    result["customFields"] = custom_fields

    if memory_root:
        write_custom_fields(memory_root, result["identifier"], project_data["id"], type_ids, custom_fields)

print(json.dumps(result, indent=2))
