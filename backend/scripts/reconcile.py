"""Daily Razorpay reconciliation. Run from cron: `cd backend && python -m scripts.reconcile`."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from billing import razorpay_request  # noqa: E402
from billing_sync import reconcile  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(asyncio.run(reconcile(razorpay_request)), default=str))
