"""Collect market data now: `python -m app.market_pulse.refresh` (run from backend/).

Use this from a daily scheduler (cron, Railway cron, Task Scheduler) so a snapshot is stored even
on days when nobody opens the Home page.
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from . import service, storage

if __name__ == "__main__":
    load_dotenv(Path(__file__).parents[2] / ".env", override=False)
    print(f"Collecting job listings into {storage.engine()}...", flush=True)
    summary = service.refresh()
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["status"] in ("ok", "partial") else 1)
