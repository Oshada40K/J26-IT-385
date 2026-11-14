"""Environment configuration for Career Market Pulse. Every value is read at call time."""
import os
from pathlib import Path

MARKETS = {
    "global": {
        "label": "Global",
        "description": "Every listing collected from the connected job boards, with duplicates removed. "
                       "Coverage follows the sources: Arbeitnow is Europe-focused.",
    },
    "remote": {
        "label": "Remote",
        "description": "Listings the source marks as remote.",
    },
    "sri_lanka": {
        "label": "Sri Lanka",
        "description": "Remote roles open to candidates based in Sri Lanka (Himalayas country filter), remote roles "
                       "open worldwide on the other boards, and any listing located in Sri Lanka. No connected source "
                       "publishes on-site Sri Lankan vacancies.",
    },
}

GROWTH_WINDOW_DAYS = 7      # latest 7-day average vs the previous 7-day average
BACKFILL_DAYS = 6           # full days of posting dates still listed when collection starts
MAX_SNAPSHOT_GAP_DAYS = 6   # longer gaps lose postings that left the feeds in between
MIN_GROWTH_BASELINE = 5     # postings needed in the previous window for a meaningful percentage
MIN_SALARY_SAMPLE = 5       # listings with disclosed pay needed to publish a median
RETAIN_LISTING_DAYS = 120
USER_AGENT = "CareerNova-MarketPulse/1.0 (university research project J26-IT-385)"


def _number(name, default, cast=float):
    try:
        return cast(os.getenv(name, default))
    except ValueError:
        return cast(default)


def database_url():
    """PostgreSQL URL when one is really configured (the .env.example placeholder is ignored)."""
    url = (os.getenv("MARKET_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not url.startswith(("postgresql://", "postgres://")) or "username:password@" in url:
        return None
    return url


def sqlite_path():
    default = Path(__file__).parents[2] / ".data" / "market.sqlite3"
    return Path(os.getenv("MARKET_DATABASE_PATH", str(default)))


def auto_refresh():
    return os.getenv("MARKET_AUTO_REFRESH", "true").lower() == "true"


def refresh_hours():
    return max(1.0, _number("MARKET_REFRESH_HOURS", "12"))


def active_hours():
    """A listing counts as open while a source has returned it within this many hours."""
    return max(refresh_hours() * 2, _number("MARKET_ACTIVE_HOURS", "48"))


def arbeitnow_max_pages():
    return _number("MARKET_ARBEITNOW_MAX_PAGES", "45", int)


def himalayas_max_pages():
    return _number("MARKET_HIMALAYAS_MAX_PAGES", "90", int)


def jobicy_max_pages():
    """Jobicy pages of 100 listings; its 7-day feed is normally well under this limit."""
    return _number("MARKET_JOBICY_MAX_PAGES", "40", int)
