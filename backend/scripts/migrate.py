"""Create/upgrade all MongoDB indexes (idempotent). Run before first deploy: `cd backend && python -m scripts.migrate`."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from server import ensure_indexes  # noqa: E402

if __name__ == "__main__":
    asyncio.run(ensure_indexes())
    print("Indexes ensured.")
