"""Repo-relative paths for tests (no hard-coded /app). Override with env vars on CI or another machine."""
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("GYMBOSS_ROOT") or Path(__file__).resolve().parents[2])
BACKEND_DIR = ROOT / "backend"
BACKEND_ENV = Path(os.environ.get("GYMBOSS_BACKEND_ENV") or BACKEND_DIR / ".env")
FRONTEND_ENV = Path(os.environ.get("GYMBOSS_FRONTEND_ENV") or ROOT / "frontend" / ".env")
CREDENTIALS = Path(os.environ.get("GYMBOSS_TEST_CREDENTIALS") or ROOT / "memory" / "test_credentials.md")

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
