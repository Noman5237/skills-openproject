#!/usr/bin/env python3
"""Add a user to an OpenProject project with a specified role.

Usage:
    python3 add_member.py --user-id USER_ID --project-id PROJECT_ID [--role-id ROLE_ID]

Output JSON (stdout):
    {
        "success": true,
        "userId": 118,
        "userName": "M M Nazmul Hossain",
        "projectId": 83,
        "projectName": "Zoober Pay",
        "roleName": "Member"
    }

    or on error:

    {
        "success": false,
        "error": "error message"
    }
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

sys.path.insert(
    0,
    __import__("os").path.join(
        __import__("os").path.dirname(__file__), "..", "..", "..", "scripts"
    ),
)
from op_env import get_api_config

_OP_BASE, BASE_URL, WP_BASE, _headers = get_api_config()


def _get(url):
    req = urllib.request.Request(url, headers=_headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _post(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=_headers, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def add_member(user_id: int, project_id: int, role_id: int = 6):
    """Add user to project with the given role."""
    body = {
        "_links": {
            "project": {"href": f"/api/v3/projects/{project_id}"},
            "principal": {"href": f"/api/v3/users/{user_id}"},
            "roles": [{"href": f"/api/v3/roles/{role_id}"}],
        }
    }

    result = _post(f"{BASE_URL}/memberships", body)

    return {
        "success": True,
        "userId": user_id,
        "userName": result["_links"]["principal"]["title"],
        "projectId": project_id,
        "projectName": result["_links"]["project"]["title"],
        "roleName": result["_links"]["roles"][0]["title"],
    }


def list_roles():
    """List all available roles."""
    data = _get(f"{BASE_URL}/roles")
    roles = []
    for role in data["_embedded"]["elements"]:
        roles.append({"id": role["id"], "name": role["name"]})
    return roles


def list_members(project_id: int):
    """List current members of a project."""
    filters = json.dumps([{"project": {"operator": "=", "values": [str(project_id)]}}])
    url = f"{BASE_URL}/memberships?filters={urllib.parse.quote(filters)}&pageSize=200"
    data = _get(url)
    members = []
    for m in data["_embedded"]["elements"]:
        members.append({
            "userId": m["_links"]["principal"]["href"].split("/")[-1],
            "userName": m["_links"]["principal"]["title"],
            "roles": [r["title"] for r in m["_links"]["roles"]],
        })
    return members


def main():
    parser = argparse.ArgumentParser(description="Add user to OpenProject project")
    parser.add_argument("--user-id", type=int, required=True, help="User ID")
    parser.add_argument("--project-id", type=int, required=True, help="Project ID")
    parser.add_argument("--role-id", type=int, default=6, help="Role ID (default: 6 = Member)")
    parser.add_argument("--list-roles", action="store_true", help="List available roles")
    parser.add_argument("--list-members", action="store_true", help="List project members")
    args = parser.parse_args()

    try:
        if args.list_roles:
            print(json.dumps(list_roles(), indent=2))
        elif args.list_members:
            print(json.dumps(list_members(args.project_id), indent=2))
        else:
            result = add_member(args.user_id, args.project_id, args.role_id)
            print(json.dumps(result, indent=2))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            error_data = json.loads(error_body)
            message = error_data.get("message", error_body)
        except json.JSONDecodeError:
            message = error_body
        print(json.dumps({"success": False, "error": f"HTTP {e.code}: {message}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
