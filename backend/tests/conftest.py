import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL is missing from the process environment and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def api_url():
    return API


@pytest.fixture(scope="function")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s
    s.close()


@pytest.fixture(scope="session")
def creds():
    """Parse /app/memory/test_credentials.md for demo + super admin credentials."""
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("Missing /app/memory/test_credentials.md")
    content = p.read_text(encoding="utf-8")
    emails = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    usernames = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Username(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    passwords = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    if not passwords:
        pytest.skip("No credentials found in test_credentials.md")
    return {
        "super_admin": {"identifier": usernames[0], "password": passwords[0]},
        "demo": {"identifier": emails[0], "password": passwords[1] if len(passwords) > 1 else passwords[0]},
    }


@pytest.fixture(scope="function")
def demo_client(client, creds):
    r = client.post(f"{API}/auth/login", json=creds["demo"])
    if r.status_code != 200:
        pytest.fail(f"Demo login failed {r.status_code}: {r.text[:300]}")
    return client


def unique_email(prefix="test_qa"):
    # server lowercases emails, so keep fixtures lowercase for round-trip assertions
    return f"{prefix}_{uuid.uuid4().hex[:10]}@testgym.in".lower()


def unique_phone():
    n = uuid.uuid4().int % 1000000000
    return "9" + str(n).zfill(9)
