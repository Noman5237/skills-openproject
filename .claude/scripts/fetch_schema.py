#!/usr/bin/env python3
"""Fetch and extract custom fields from a project+type work package schema.

Usage:
    python3 fetch_schema.py <project_id> <type_id>

Output (stdout):
    {
        "customFields": [
            {
                "fieldKey": "customField1",
                "label": "WBS",
                "type": "text",
                "required": true,
                "allowedValues": null,
                "notes": ""
            },
            ...
        ]
    }

The output is ready to merge into .memory/projects/{slug}/custom-fields.json.
For list-type fields, allowedValues contains [{id, value}] pairs where id is the
custom_option ID used in _links when creating/updating work packages.
"""

import json
import os
import sys
import urllib.error
import urllib.request

from op_env import get_api_config

_OP_BASE, BASE_URL, _WP_BASE, headers = get_api_config()

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <project_id> <type_id>", file=sys.stderr)
    sys.exit(1)

project_id = sys.argv[1]
type_id = sys.argv[2]


def fetch_json(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Error fetching {url}: HTTP {e.code} — {body}", file=sys.stderr)
        sys.exit(1)


schema_url = f"{BASE_URL}/work_packages/schemas/{project_id}-{type_id}"
schema = fetch_json(schema_url)

custom_fields = []
for key in sorted(schema.keys()):
    if not key.startswith("customField"):
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
        # List-type field — extract option IDs and values
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

print(json.dumps({"customFields": custom_fields}, indent=2))
