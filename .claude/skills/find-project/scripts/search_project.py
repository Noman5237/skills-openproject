#!/usr/bin/env python3
"""Search OpenProject projects by name or identifier (substring match).

Usage:
    python3 search_project.py <name>
    python3 search_project.py <name> --cache-dir /path/to/.memory/projects

Examples:
    python3 search_project.py CityRemit
    python3 search_project.py devops
"""

import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import get_api_config

_OP_BASE, BASE_URL, _WP_BASE, _headers = get_api_config()


def find_memory_root():
    """Walk up from cwd to find .memory/projects directory."""
    d = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(d, ".memory", "projects")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def write_meta(cache_dir, project):
    """Write meta.json for a project into cache_dir/{identifier}/."""
    identifier = project["identifier"]
    proj_dir = os.path.join(cache_dir, identifier)
    os.makedirs(proj_dir, exist_ok=True)
    meta = {
        "id": project["id"],
        "name": project["name"],
        "identifier": identifier,
        "status": project["status"],
        "cachedAt": datetime.date.today().isoformat(),
    }
    with open(os.path.join(proj_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <name> [--cache-dir PATH]", file=sys.stderr)
    sys.exit(1)

name = sys.argv[1]
cache_dir = None
i = 2
while i < len(sys.argv):
    if sys.argv[i] == "--cache-dir" and i + 1 < len(sys.argv):
        cache_dir = sys.argv[i + 1]
        i += 2
    else:
        i += 1

if cache_dir is None:
    cache_dir = find_memory_root()

filters = [{"name_and_identifier": {"operator": "~", "values": [name]}}]
params = urllib.parse.urlencode({"filters": json.dumps(filters), "pageSize": 50})
url = f"{BASE_URL}/projects?{params}"

req = urllib.request.Request(url, headers=_headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

results = []
for el in data.get("_embedded", {}).get("elements", []):
    status_href = el.get("_links", {}).get("status", {}).get("href", "")
    status_title = el.get("_links", {}).get("status", {}).get("title", "")
    project = {
        "id": el["id"],
        "name": el["name"],
        "identifier": el["identifier"],
        "status": status_title or None,
    }
    results.append(project)
    if cache_dir:
        write_meta(cache_dir, project)

print(json.dumps(results, indent=2))
