"""Fetches live job listings from public job boards and normalises them to one shape.

Every fetcher is a generator of listing dicts:
    source, source_id, url, title, company, location, is_remote, is_sri_lanka,
    posted_at (aware UTC datetime), salary_usd (annual, or None), career, skills
Descriptions are only scanned for skills; they are never stored or republished.
Sources ask for attribution and a link back, which the Home page shows from SOURCES.
"""
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx

from . import config
from .taxonomy import classify_career, extract_skills, plain_text

SOURCES = {
    "arbeitnow": {"label": "Arbeitnow", "url": "https://www.arbeitnow.com",
                  "coverage": "Full public feed (about the last 7 days). Europe-focused, mostly Germany."},
    "remoteok": {"label": "Remote OK", "url": "https://remoteok.com",
                 "coverage": "Full public feed of remote roles."},
    "remotive": {"label": "Remotive", "url": "https://remotive.com",
                 "coverage": "Public feed of remote roles (a small, 24-hour-delayed subset)."},
    "himalayas": {"label": "Himalayas", "url": "https://himalayas.app",
                  "coverage": "Remote roles open to candidates in Sri Lanka (country filter)."},
    "jobicy": {"label": "Jobicy", "url": "https://jobicy.com",
               "coverage": "Full public feed of remote roles from the last 7 days, worldwide (many in the USA)."},
}

_SRI_LANKA = re.compile(r"sri lanka|colombo", re.I)
_WORLDWIDE = re.compile(r"worldwide|anywhere|global", re.I)
_NOT_ANNUAL = re.compile(r"hour|/\s?h\b|/hr|month|/mo\b|week|day|task|project", re.I)
_USD_AMOUNT = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?(k)?", re.I)
_PERIODS = {"annual": 1, "annually": 1, "yearly": 1, "year": 1, "monthly": 12, "month": 12}
SALARY_BAND = (10_000, 600_000)


def annual_usd(low, high, currency="USD", period="annual"):
    """Midpoint of a disclosed USD salary as a yearly amount, or None when it cannot be trusted.

    Only yearly and monthly (x12) pay is used: hourly, daily and per-task rates are excluded because
    annualising contract rates overstates pay. Other currencies are excluded instead of converted.
    """
    if (currency or "USD").upper() != "USD":
        return None
    multiplier = _PERIODS.get((period or "annual").lower())
    try:
        values = [float(v) for v in (low, high) if v not in (None, "") and float(v) > 0]
    except (TypeError, ValueError):
        return None
    if not values or multiplier is None:
        return None
    amounts = [v * multiplier for v in values]
    if any(not SALARY_BAND[0] <= a <= SALARY_BAND[1] for a in amounts):
        return None
    return round(sum(amounts) / len(amounts), 2)


def parse_usd_salary(text):
    """Free-text salary such as "$120k - $150k" -> annual USD midpoint; None unless clearly yearly USD."""
    if not text or "$" not in text or _NOT_ANNUAL.search(text):
        return None
    amounts = [float(number.replace(",", "")) * (1000 if k else 1) for number, k in _USD_AMOUNT.findall(text)][:2]
    return annual_usd(amounts[0], amounts[-1]) if amounts else None


def _utc(value):
    """Unix seconds or an ISO string -> aware UTC datetime (naive strings are treated as UTC)."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _listing(source, source_id, url, title, company, location, posted_at, *, remote, sri_lanka=False,
             salary_usd=None, tags=(), description=""):
    title, location = " ".join(html.unescape(title or "").split()), (location or "").strip()
    return {
        "source": source, "source_id": str(source_id), "url": url or "", "title": title[:300],
        "company": html.unescape(company or "").strip()[:200], "location": location[:200],
        "is_remote": bool(remote), "is_sri_lanka": bool(sri_lanka or _SRI_LANKA.search(location)),
        "posted_at": _utc(posted_at), "salary_usd": salary_usd,
        "career": classify_career(title),
        "skills": extract_skills(title, " , ".join(tags or ()), plain_text(description)),
    }


def _get(client, url, params=None):
    """GET JSON, waiting and retrying when a board rate-limits us or has a server error."""
    for attempt in range(4):
        response = client.get(url, params=params)
        if response.status_code not in (429, 500, 502, 503, 504) or attempt == 3:
            response.raise_for_status()
            return response.json()
        wait = response.headers.get("Retry-After", "")
        time.sleep(min(int(wait), 90) if wait.isdigit() else 15 * (attempt + 1))


def fetch_arbeitnow(client, pause=0.5):
    for page in range(1, config.arbeitnow_max_pages() + 1):
        data = _get(client, "https://www.arbeitnow.com/api/job-board-api", {"page": page})
        jobs = data.get("data") or []
        for job in jobs:
            yield _listing("arbeitnow", job["slug"], job.get("url"), job.get("title"), job.get("company_name"),
                           job.get("location"), job["created_at"], remote=job.get("remote"),
                           tags=job.get("tags"), description=job.get("description"))
        if not jobs or not (data.get("links") or {}).get("next"):
            return
        time.sleep(pause)


def fetch_remoteok(client):
    for job in _get(client, "https://remoteok.com/api"):
        if not job.get("id") or not job.get("position"):
            continue  # the first element is the API's legal notice
        location = job.get("location") or ""
        yield _listing("remoteok", job["id"], job.get("url"), job["position"], job.get("company"), location,
                       job.get("epoch") or job["date"], remote=True, sri_lanka=_WORLDWIDE.search(location),
                       salary_usd=annual_usd(job.get("salary_min"), job.get("salary_max")),
                       tags=job.get("tags"), description=job.get("description"))


def fetch_remotive(client):
    for job in _get(client, "https://remotive.com/api/remote-jobs").get("jobs") or []:
        location = job.get("candidate_required_location") or ""
        yield _listing("remotive", job["id"], job.get("url"), job.get("title"), job.get("company_name"), location,
                       job["publication_date"], remote=True, sri_lanka=_WORLDWIDE.search(location),
                       salary_usd=parse_usd_salary(job.get("salary")),
                       tags=job.get("tags"), description=job.get("description"))


def fetch_himalayas(client, pause=1.0):
    for page in range(1, config.himalayas_max_pages() + 1):
        data = _get(client, "https://himalayas.app/jobs/api/search", {"country": "LK", "page": page})
        jobs = data.get("jobs") or []
        for job in jobs:
            yield _listing("himalayas", job.get("guid") or job["applicationLink"], job.get("applicationLink"),
                           job.get("title"), job.get("companyName"),
                           ", ".join(job.get("locationRestrictions") or []) or "Worldwide", job["pubDate"],
                           remote=True, sri_lanka=True,
                           salary_usd=annual_usd(job.get("minSalary"), job.get("maxSalary"),
                                                 job.get("currency"), job.get("salaryPeriod")),
                           tags=[*(job.get("categories") or []), *(job.get("parentCategories") or [])],
                           description=job.get("description") or job.get("excerpt"))
        if not jobs or page * len(jobs) >= int(data.get("totalCount") or 0):
            return
        time.sleep(pause)


def fetch_jobicy(client, pause=1.5):
    """Jobicy's free feed: remote roles from the last 7 days, 100 per page, paged with a cursor."""
    cursor = None
    for _ in range(config.jobicy_max_pages()):
        data = _get(client, "https://jobicy.com/api/v2/remote-jobs", {"count": 100, **({"cursor": cursor} if cursor else {})})
        jobs = data.get("jobs") or []
        for job in jobs:
            location = job.get("jobGeo") or ""
            # A salary without a stated period is skipped rather than assumed to be yearly.
            salary = annual_usd(job.get("salaryMin"), job.get("salaryMax"), job.get("salaryCurrency"),
                                job.get("salaryPeriod") or "unknown")
            yield _listing("jobicy", job["id"], job.get("url"), job.get("jobTitle"), job.get("companyName"), location,
                           job["pubDate"], remote=True, sri_lanka=_WORLDWIDE.search(location), salary_usd=salary,
                           tags=job.get("jobIndustry") or [], description=job.get("jobDescription") or job.get("jobExcerpt"))
        cursor = data.get("nextCursor")
        if not jobs or not cursor or str(data.get("hasMore")).lower() != "true":
            return
        time.sleep(pause)


FETCHERS = {"arbeitnow": fetch_arbeitnow, "remoteok": fetch_remoteok, "remotive": fetch_remotive,
            "himalayas": fetch_himalayas, "jobicy": fetch_jobicy}


def _run(name):
    """Runs one fetcher. Listings received before a failure are kept and the source is marked partial."""
    listings, error = [], None
    try:
        with httpx.Client(headers={"User-Agent": config.USER_AGENT}, follow_redirects=True,
                          timeout=httpx.Timeout(60, connect=15)) as client:
            for listing in FETCHERS[name](client):
                listings.append(listing)
    except Exception as exc:  # one failing board must not stop the others
        # Query strings (page numbers, long cursors) are removed to keep the message short.
        error = re.sub(r"\?[^\s'\"]+", "", f"{type(exc).__name__}: {exc}")[:300]
    return listings, {"source": name, "ok": bool(listings), "partial": bool(listings and error),
                      "fetched": len(listings), "error": error}


def collect():
    """Fetches every source in parallel. Returns (listings, per-source statuses)."""
    with ThreadPoolExecutor(max_workers=len(FETCHERS)) as pool:
        results = list(pool.map(_run, FETCHERS))
    listings = [listing for found, _ in results for listing in found]
    return listings, [status for _, status in results]
