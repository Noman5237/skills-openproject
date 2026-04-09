#!/usr/bin/env python3
"""Search OpenProject work packages with composable filters.

All filter flags are optional and combine as AND logic. When --with-children is
given, direct children of matched items are fetched in a second query and nested
under their parent in the output (exactly 1 level deep).

Usage examples:
    python3 search_work_packages.py --assignee 64 --status-open
    python3 search_work_packages.py --subject "login" --type 1,4 --due-to 2026-05-31
    python3 search_work_packages.py --project 5 --custom-option customField3=1 --with-children

Output (stdout): JSON {"total": N, "items": [...]}
Each item: id, subject, type, status, project, assignee, responsible,
           startDate, dueDate, work, spent, parent, link, children
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
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
        print(f"Error: HTTP {e.code} from {url}\n{body}", file=sys.stderr)
        sys.exit(1)


def fetch_all_pages(filters, page_size=100):
    """Fetch all pages for a given filter list; return flat list of elements."""
    items = []
    offset = 1
    while True:
        params = urllib.parse.urlencode({
            "filters": json.dumps(filters),
            "pageSize": page_size,
            "offset": offset,
        })
        url = f"{BASE_URL}/work_packages?{params}"
        data = fetch_json(url)
        elements = data.get("_embedded", {}).get("elements", [])
        items.extend(elements)
        total = data.get("total", 0)
        if offset * page_size >= total:
            break
        offset += 1
    return items


# ---------------------------------------------------------------------------
# Duration / field extraction
# ---------------------------------------------------------------------------

def parse_duration(iso_duration):
    """PT4H30M → '4.5h', None → '-'."""
    if not iso_duration:
        return "-"
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", iso_duration)
    if not m:
        return "-"
    hours = float(m.group(1) or 0)
    minutes = float(m.group(2) or 0)
    total = hours + minutes / 60
    return f"{total:.1f}h" if total > 0 else "-"


def extract_item(el):
    links = el.get("_links", {})
    parent_link = links.get("parent", {})
    parent_title = parent_link.get("title") if parent_link.get("href") else None

    return {
        "id": el.get("id"),
        "subject": el.get("subject", ""),
        "type": links.get("type", {}).get("title", "-"),
        "status": links.get("status", {}).get("title", "-"),
        "project": links.get("project", {}).get("title", "-"),
        "assignee": links.get("assignee", {}).get("title") or None,
        "responsible": links.get("responsible", {}).get("title") or None,
        "startDate": el.get("startDate") or None,
        "dueDate": el.get("dueDate") or None,
        "work": parse_duration(el.get("estimatedTime")),
        "spent": parse_duration(el.get("spentTime")),
        "parent": parent_title,
        "createdAt": el.get("createdAt"),
        "link": f"{WP_BASE}/{el.get('id')}",
        "children": [],
    }


# ---------------------------------------------------------------------------
# Argument → filter building
# ---------------------------------------------------------------------------

def build_filters(args):
    filters = []

    if args.project:
        filters.append({"project": {"operator": "=", "values": [str(args.project)]}})

    if args.id:
        ids = [v.strip() for v in args.id.split(",") if v.strip()]
        filters.append({"id": {"operator": "=", "values": ids}})

    if args.subject:
        filters.append({"subject": {"operator": "~", "values": [args.subject]}})

    if args.assignee:
        filters.append({"assignee": {"operator": "=", "values": [str(args.assignee)]}})

    if args.responsible:
        filters.append({"responsible": {"operator": "=", "values": [str(args.responsible)]}})

    if args.status_open:
        filters.append({"status": {"operator": "o", "values": []}})
    elif args.status:
        ids = [v.strip() for v in args.status.split(",") if v.strip()]
        filters.append({"status": {"operator": "=", "values": ids}})

    if args.type:
        ids = [v.strip() for v in args.type.split(",") if v.strip()]
        filters.append({"type": {"operator": "=", "values": ids}})

    # OpenProject date fields require the <> d (between) operator with two values.
    # Use sentinel dates when only one bound is provided.
    if args.start_from or args.start_to:
        filters.append({"startDate": {"operator": "<>d", "values": [
            args.start_from or "0001-01-01",
            args.start_to or "9999-12-31",
        ]}})

    if args.due_from or args.due_to:
        filters.append({"dueDate": {"operator": "<>d", "values": [
            args.due_from or "0001-01-01",
            args.due_to or "9999-12-31",
        ]}})

    if args.created_before or args.created_after:
        filters.append({"createdAt": {"operator": "<>d", "values": [
            args.created_after or "0001-01-01",
            args.created_before or "9999-12-31",
        ]}})

    # Custom text fields: substring match
    for pair in (args.custom_text or []):
        if "=" not in pair:
            print(f"Warning: --custom-text '{pair}' ignored (expected KEY=VALUE)", file=sys.stderr)
            continue
        key, value = pair.split("=", 1)
        filters.append({key.strip(): {"operator": "~", "values": [value.strip()]}})

    # Custom list/option fields: exact option ID match
    for pair in (args.custom_option or []):
        if "=" not in pair:
            print(f"Warning: --custom-option '{pair}' ignored (expected KEY=OPTION_ID)", file=sys.stderr)
            continue
        key, option_id = pair.split("=", 1)
        filters.append({key.strip(): {"operator": "=", "values": [option_id.strip()]}})

    return filters


# ---------------------------------------------------------------------------
# Children fetching
# ---------------------------------------------------------------------------

def fetch_children(parent_ids):
    """Return a dict {parent_id: [child_items]} for all given parent IDs."""
    if not parent_ids:
        return {}

    # Batch in groups of 50 to avoid overly long URLs
    batch_size = 50
    children_map = {}
    for i in range(0, len(parent_ids), batch_size):
        batch = [str(pid) for pid in parent_ids[i : i + batch_size]]
        filters = [{"parent": {"operator": "=", "values": batch}}]
        elements = fetch_all_pages(filters)
        for el in elements:
            child = extract_item(el)
            parent_href = el.get("_links", {}).get("parent", {}).get("href", "")
            try:
                pid = int(parent_href.split("/")[-1])
            except (ValueError, IndexError):
                continue
            children_map.setdefault(pid, []).append(child)

    return children_map


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Search OpenProject work packages with composable filters"
    )
    parser.add_argument("--project", help="Scope to project numeric ID")
    parser.add_argument("--subject", help="Subject contains TEXT (substring)")
    parser.add_argument("--id", help="Specific WP IDs, comma-separated")
    parser.add_argument("--assignee", help="Assignee numeric user ID")
    parser.add_argument("--responsible", help="Responsible/accountable numeric user ID")
    parser.add_argument("--status", help="Status IDs, comma-separated")
    parser.add_argument("--status-open", action="store_true",
                        help="All non-closed statuses (overrides --status)")
    parser.add_argument("--type", help="Type IDs, comma-separated")
    parser.add_argument("--start-from", dest="start_from", metavar="DATE",
                        help="startDate >= DATE (YYYY-MM-DD)")
    parser.add_argument("--start-to", dest="start_to", metavar="DATE",
                        help="startDate <= DATE")
    parser.add_argument("--due-from", dest="due_from", metavar="DATE",
                        help="dueDate >= DATE")
    parser.add_argument("--due-to", dest="due_to", metavar="DATE",
                        help="dueDate <= DATE")
    parser.add_argument("--created-before", dest="created_before", metavar="DATE",
                        help="createdAt <= DATE (YYYY-MM-DD)")
    parser.add_argument("--created-after", dest="created_after", metavar="DATE",
                        help="createdAt >= DATE (YYYY-MM-DD)")
    parser.add_argument("--custom-text", metavar="KEY=VALUE", action="append",
                        help="Custom text field substring filter (repeatable)")
    parser.add_argument("--custom-option", metavar="KEY=OPTION_ID", action="append",
                        help="Custom list field exact option ID filter (repeatable)")
    parser.add_argument("--with-children", action="store_true",
                        help="Also fetch direct children of matched items (1 level)")
    args = parser.parse_args()

    filters = build_filters(args)
    elements = fetch_all_pages(filters)
    items = [extract_item(el) for el in elements]

    if args.with_children and items:
        parent_ids = [item["id"] for item in items]
        children_map = fetch_children(parent_ids)
        for item in items:
            item["children"] = children_map.get(item["id"], [])

    print(json.dumps({"total": len(items), "items": items}, indent=2))


if __name__ == "__main__":
    main()
