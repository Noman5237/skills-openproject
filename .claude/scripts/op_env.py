"""Shared OpenProject environment and API configuration.

All skill scripts import from here instead of duplicating .env loading,
API key validation, and credential setup.
"""

import base64
import os
import sys


def load_dotenv():
    """Load .env file by walking up from cwd and caller's directory."""
    for base in (os.getcwd(), os.path.dirname(os.path.abspath(sys.argv[0]))):
        d = base
        for _ in range(10):
            env_path = os.path.join(d, ".env")
            if os.path.isfile(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ.setdefault(k.strip(), v.strip())
                return
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent


def get_api_config():
    """Load .env, validate API key, and return (op_base, api_url, wp_url, headers).

    Exits with code 1 if OPENPROJECT_API_KEY is not set.
    """
    load_dotenv()

    op_base = os.environ.get(
        "OPENPROJECT_BASE_URL", "http://project.global.fintech23.xyz"
    ).rstrip("/")
    api_url = op_base + "/api/v3"
    wp_url = op_base + "/work_packages"

    api_key = os.environ.get("OPENPROJECT_API_KEY")
    if not api_key:
        print("Error: OPENPROJECT_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    credentials = base64.b64encode(f"apikey:{api_key}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }

    return op_base, api_url, wp_url, headers
