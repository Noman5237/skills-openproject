#!/usr/bin/env python3
"""Get OpenProject user details by numeric ID.

Usage: python3 get_user.py <user_id>

Example:
    python3 get_user.py 64
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from op_env import get_api_config

_OP_BASE, BASE_URL, _WP_BASE, _headers = get_api_config()

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <user_id>", file=sys.stderr)
    sys.exit(1)

user_id = sys.argv[1]
url = f"{BASE_URL}/users/{user_id}"

req = urllib.request.Request(url, headers=_headers)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

result = {
    "id": data.get("id"),
    "name": data.get("name"),
    "login": data.get("login"),
    "email": data.get("email"),
    "status": data.get("status"),
    "admin": data.get("admin"),
}

print(json.dumps(result, indent=2))
