#!/usr/bin/env python3
"""Search OpenProject users/principals by name (substring match).

Usage: python3 search_user.py <name> [--users-only]

Examples:
    python3 search_user.py Noman
    python3 search_user.py Noman --users-only
"""

import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import get_api_config

_OP_BASE, BASE_URL, _WP_BASE, _headers = get_api_config()

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <name> [--users-only]", file=sys.stderr)
    sys.exit(1)

name = sys.argv[1]
users_only = len(sys.argv) > 2 and sys.argv[2] == "--users-only"

filters = [{"name": {"operator": "~", "values": [name]}}]
if users_only:
    filters.append({"type": {"operator": "=", "values": ["User"]}})

params = urllib.parse.urlencode({"filters": json.dumps(filters), "pageSize": 20})
url = f"{BASE_URL}/principals?{params}"

req = urllib.request.Request(url, headers=_headers)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

results = [
    {"id": el["id"], "name": el["name"], "type": el["_type"]}
    for el in data.get("_embedded", {}).get("elements", [])
]

print(json.dumps(results, indent=2))
