"""Collects listings, stores daily snapshots and answers the Home page's market questions.

How the numbers are produced
  * A refresh fetches every source, removes duplicates and upserts market_listings.
  * "Active listings" are listings a source returned within the last active_hours().
  * "New postings" for a day are the stored listings whose posting date is that day. Because
    listings are kept after they leave a feed, a day's count stays correct on later refreshes.
  * Career growth compares the average daily new postings of the latest 7 complete days with the
    previous 7. It is only reported once 14 days have been collected without a long gap, so a
    percentage is never produced from partial history.
Nothing here is estimated or simulated: when data is missing the API says so instead.
"""
import hashlib
import json
import logging
import re
import statistics
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from . import config, sources, storage
from .taxonomy import CAREERS

log = logging.getLogger("market_pulse")

MARKET_FILTERS = {
    "global": lambda row: True,
    "remote": lambda row: bool(row["is_remote"]),
    "sri_lanka": lambda row: bool(row["is_sri_lanka"]),
}
SALARY_BASIS = ("Annual pay in USD as disclosed in the listing (monthly pay x12). Hourly and per-task rates, "
                "other currencies are excluded.")
_GENDER = re.compile(r"\(\s*[a-z*]{1,5}\s*(/\s*[a-z*]{1,5}\s*){1,3}\)|\ball genders\b", re.I)
# A collection takes a few minutes. A run still marked "running" after this long was cut off
# (for example by a server restart or `uvicorn --reload`) and is started again.
ABANDONED_RUN_SECONDS = 900
_refresh_lock = threading.Lock()
_refresh_thread = None
_last_check = 0.0


def now():
    return datetime.now(timezone.utc)


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _normal(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def listing_key(listing):
    """Identity of a job across sources: title + company, plus the location for on-site roles."""
    if not listing["company"]:
        parts = [listing["source"], listing["source_id"]]
    else:
        parts = [_normal(_GENDER.sub(" ", listing["title"])), _normal(listing["company"])]
        if not listing["is_remote"]:
            parts.append(_normal(listing["location"]))
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:24]


def dedupe(listings):
    """Merges repeated listings. Returns (unique listings by key, number of duplicates removed)."""
    unique = {}
    for listing in listings:
        key = listing_key(listing)
        kept = unique.get(key)
        if kept is None:
            unique[key] = dict(listing)
            continue
        kept["is_remote"] = kept["is_remote"] or listing["is_remote"]
        kept["is_sri_lanka"] = kept["is_sri_lanka"] or listing["is_sri_lanka"]
        kept["posted_at"] = min(kept["posted_at"], listing["posted_at"])
        kept["salary_usd"] = kept["salary_usd"] or listing["salary_usd"]
        kept["skills"] = sorted({*kept["skills"], *listing["skills"]})
    return unique, len(listings) - len(unique)


# ---------- collection ----------

def store_listings(db, unique, moment):
    seen, today = stamp(moment), moment.date()
    db.insert_many(
        """INSERT INTO market_listings (listing_key, source, source_id, url, title, company, location, career, skills,
                                        is_remote, is_sri_lanka, salary_usd, posted_date, first_seen, last_seen)
           VALUES {values}
           ON CONFLICT (listing_key) DO UPDATE SET
               url = excluded.url, career = excluded.career, skills = excluded.skills, last_seen = excluded.last_seen,
               salary_usd = COALESCE(excluded.salary_usd, market_listings.salary_usd),
               is_remote = CASE WHEN excluded.is_remote = 1 OR market_listings.is_remote = 1 THEN 1 ELSE 0 END,
               is_sri_lanka = CASE WHEN excluded.is_sri_lanka = 1 OR market_listings.is_sri_lanka = 1 THEN 1 ELSE 0 END""",
        [(key, item["source"], item["source_id"], item["url"], item["title"], item["company"], item["location"],
          item["career"], json.dumps(item["skills"]), int(item["is_remote"]), int(item["is_sri_lanka"]),
          item["salary_usd"], min(item["posted_at"].date(), today).isoformat(), seen, seen)
         for key, item in unique.items()])


def _salary_stats(values):
    if not values:
        return (None, None, None, 0)
    quartiles = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else [values[0]] * 3
    return (round(statistics.median(values)), round(quartiles[0]), round(quartiles[2]), len(values))


def build_snapshot(db, moment):
    """Writes today's snapshot for every market and refreshes the trailing new-posting counts."""
    today = moment.date().isoformat()
    cutoff = stamp(moment - timedelta(hours=config.active_hours()))
    window_start = (moment.date() - timedelta(days=35)).isoformat()
    rows = db.query(
        """SELECT career, skills, is_remote, is_sri_lanka, salary_usd, company, posted_date, last_seen
           FROM market_listings WHERE last_seen >= ? OR posted_date >= ?""", (cutoff, window_start))
    snapshot, trailing = [], []
    for market, belongs in MARKET_FILTERS.items():
        members = [row for row in rows if belongs(row)]
        active = [row for row in members if row["last_seen"] >= cutoff]
        new = Counter()  # (kind, key, date) -> listings posted that day
        for row in members:
            if row["posted_date"] >= window_start:
                new["total", "listings", row["posted_date"]] += 1
                if row["career"]:
                    new["career", row["career"], row["posted_date"]] += 1
        salaries = defaultdict(list)
        for row in active:
            if row["salary_usd"]:
                salaries[None].append(row["salary_usd"])
                if row["career"]:
                    salaries[row["career"]].append(row["salary_usd"])
        careers = Counter(row["career"] for row in active if row["career"])
        skills = Counter(skill for row in active for skill in json.loads(row["skills"]))
        meta = {
            "companies": len({_normal(row["company"]) for row in active if row["company"]}),
            "tracked": sum(careers.values()),
            "remote": sum(1 for row in active if row["is_remote"]),
            "with_skills": sum(1 for row in active if row["skills"] != "[]"),
        }
        snapshot.append((today, market, "total", "listings", len(active), new["total", "listings", today],
                         *_salary_stats(salaries[None])))
        snapshot += [(today, market, "meta", key, value, 0, None, None, None, None) for key, value in meta.items()]
        for career in {*careers, *salaries} - {None} | {key for kind, key, day in new if kind == "career" and day == today}:
            snapshot.append((today, market, "career", career, careers[career], new["career", career, today],
                             *_salary_stats(salaries.get(career, []))))
        snapshot += [(today, market, "skill", skill, count, 0, None, None, None, None) for skill, count in skills.items()]
        trailing += [(day, market, kind, key, count) for (kind, key, day), count in new.items() if day < today]

    db.execute("DELETE FROM market_daily_stats WHERE snapshot_date = ?", (today,))
    db.execute("UPDATE market_daily_stats SET new_count = 0 WHERE snapshot_date >= ? AND snapshot_date < ?",
               (window_start, today))
    db.insert_many(
        """INSERT INTO market_daily_stats (snapshot_date, market, kind, stat_key, active_count, new_count,
                                           salary_median, salary_p25, salary_p75, salary_count) VALUES {values}""", snapshot)
    db.insert_many(
        """INSERT INTO market_daily_stats (snapshot_date, market, kind, stat_key, new_count) VALUES {values}
           ON CONFLICT (snapshot_date, market, kind, stat_key) DO UPDATE SET new_count = excluded.new_count""", trailing)


def refresh():
    """Runs one full collection and returns its summary. Safe to call from a scheduler or the CLI."""
    started, run_id = now(), uuid.uuid4().hex
    with storage.connection() as db:
        db.execute("INSERT INTO market_refresh_runs (run_id, started_at, status) VALUES (?, ?, 'running')",
                   (run_id, stamp(started)))
    summary = {"run_id": run_id, "status": "failed", "listings": 0, "duplicates": 0, "sources": [], "error": None}
    try:
        listings, summary["sources"] = sources.collect()
        if not listings:
            summary["error"] = "No source returned any listings."
        else:
            unique, summary["duplicates"] = dedupe(listings)
            summary["listings"] = len(unique)
            moment = now()
            with storage.connection() as db:
                store_listings(db, unique, moment)
                db.execute("DELETE FROM market_listings WHERE last_seen < ?",
                           (stamp(moment - timedelta(days=config.RETAIN_LISTING_DAYS)),))
                build_snapshot(db, moment)
            incomplete = [s for s in summary["sources"] if s.get("configured", True) and (not s["ok"] or s["partial"])]
            summary["status"] = "partial" if incomplete else "ok"
    except Exception as exc:
        log.exception("Market Pulse refresh failed")
        summary["error"] = f"{type(exc).__name__}: {exc}"[:300]
    finally:
        with storage.connection() as db:
            db.execute("""UPDATE market_refresh_runs SET finished_at = ?, status = ?, listings = ?, duplicates = ?,
                          sources = ?, error = ? WHERE run_id = ?""",
                       (stamp(now()), summary["status"], summary["listings"], summary["duplicates"],
                        json.dumps(summary["sources"]), summary["error"], run_id))
    return summary


def _background_refresh():
    try:
        summary = refresh()
        log.info("Market Pulse refresh %s: %s listings", summary["status"], summary["listings"])
    except Exception:
        log.exception("Market Pulse refresh could not start")


def _refresh_due(db):
    latest = db.query("SELECT started_at, finished_at, status FROM market_refresh_runs ORDER BY started_at DESC LIMIT 1")
    if not latest:
        return True
    run, current = latest[0], now()
    age = lambda value: (current - datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds()
    if run["status"] == "running":
        return age(run["started_at"]) > ABANDONED_RUN_SECONDS
    if run["status"] == "failed":
        return age(run["started_at"]) > 900           # retry failures at most every 15 minutes
    return age(run["finished_at"]) > config.refresh_hours() * 3600


def ensure_fresh():
    """Starts a background refresh when the stored data is older than the refresh interval."""
    global _refresh_thread, _last_check
    if not config.auto_refresh() or not _refresh_lock.acquire(blocking=False):
        return
    try:
        if (_refresh_thread and _refresh_thread.is_alive()) or time.monotonic() - _last_check < 60:
            return
        _last_check = time.monotonic()
        with storage.connection() as db:
            due = _refresh_due(db)
        if due:
            _refresh_thread = threading.Thread(target=_background_refresh, name="market-pulse-refresh", daemon=True)
            _refresh_thread.start()
    finally:
        _refresh_lock.release()


# ---------- reads ----------

def _day(value):
    return date.fromisoformat(value)


def _context(db, market):
    """Shared envelope of every response: freshness, availability and growth readiness."""
    bounds = db.query("""SELECT MIN(snapshot_date) AS first_day, MAX(snapshot_date) AS latest_day FROM market_daily_stats
                         WHERE kind = 'total' AND active_count IS NOT NULL""")[0]
    runs = db.query("SELECT started_at, finished_at, status, error FROM market_refresh_runs ORDER BY started_at DESC LIMIT 20")
    done = next((run for run in runs if run["status"] in ("ok", "partial")), None)
    refreshing = bool(_refresh_thread and _refresh_thread.is_alive()) or bool(
        runs and runs[0]["status"] == "running" and runs[0]["started_at"] > stamp(now() - timedelta(seconds=ABANDONED_RUN_SECONDS)))
    context = {
        "market": market, "label": config.MARKETS[market]["label"], "description": config.MARKETS[market]["description"],
        "snapshot_date": bounds["latest_day"], "collection_started": bounds["first_day"],
        "last_updated": done["finished_at"] if done else None, "refreshing": refreshing,
        # Older than two refresh intervals: collection has been failing or the scheduler is off.
        "stale": bool(done and done["finished_at"] < stamp(now() - timedelta(hours=2 * config.refresh_hours()))),
    }
    if bounds["latest_day"]:
        context["status"], context["message"] = "ready", None
    elif refreshing:
        context["status"], context["message"] = "collecting", "The first collection is running. This takes a few minutes."
    else:
        failure = runs[0]["error"] if runs and runs[0]["status"] == "failed" else None
        context["status"] = "unavailable"
        context["message"] = (f"The last collection failed: {failure}" if failure
                              else "No market data has been collected yet.")
    return context


def _growth_readiness(db, context):
    required = 2 * config.GROWTH_WINDOW_DAYS
    readiness = {"ready": False, "days_collected": 0, "days_required": required, "reason": "collecting",
                 "method": f"Average daily new postings over the latest {config.GROWTH_WINDOW_DAYS} complete days "
                           f"compared with the previous {config.GROWTH_WINDOW_DAYS} days."}
    if not context["snapshot_date"]:
        return readiness
    first, latest = _day(context["collection_started"]), _day(context["snapshot_date"])
    readiness["days_collected"] = min((latest - first).days, required)
    if (latest - first).days < required:
        return readiness
    start = latest - timedelta(days=required)
    days = sorted(_day(row["snapshot_date"]) for row in db.query(
        """SELECT DISTINCT snapshot_date FROM market_daily_stats
           WHERE kind = 'total' AND active_count IS NOT NULL AND snapshot_date >= ?""",
        ((start - timedelta(days=config.MAX_SNAPSHOT_GAP_DAYS)).isoformat(),)))
    anchors = [day for day in days if day <= start]   # a snapshot at or just before the window opens
    days = [*anchors[-1:], *[day for day in days if day > start]]
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    if not anchors or max(gaps, default=0) > config.MAX_SNAPSHOT_GAP_DAYS:
        readiness["reason"] = "gap"   # postings that came and went during the gap were never seen
        return readiness
    readiness.update(ready=True, reason=None)
    return readiness


def _new_counts(db, market, kind, since):
    """{stat_key: {date: new postings}} from the stored snapshots."""
    counts = defaultdict(dict)
    for row in db.query("""SELECT snapshot_date, stat_key, new_count FROM market_daily_stats
                           WHERE market = ? AND kind = ? AND snapshot_date >= ?""", (market, kind, since.isoformat())):
        counts[row["stat_key"]][row["snapshot_date"]] = row["new_count"]
    return counts


def _series_start(context):
    """First day with trustworthy posting counts: a few days before collection began."""
    return _day(context["collection_started"]) - timedelta(days=config.BACKFILL_DAYS)


def _complete_days(context, count):
    """The most recent `count` complete days (the snapshot day itself is still filling up)."""
    latest, start = _day(context["snapshot_date"]), _series_start(context)
    return [day for day in (latest - timedelta(days=offset) for offset in range(count, 0, -1)) if day >= start]


def _growth(series, context, readiness):
    if not readiness["ready"]:
        return {"pct": None, "direction": None, "reason": readiness["reason"]}
    window = config.GROWTH_WINDOW_DAYS
    days = _complete_days(context, 2 * window)
    previous = sum(series.get(day.isoformat(), 0) for day in days[:window])
    current = sum(series.get(day.isoformat(), 0) for day in days[window:])
    averages = {"current_avg": round(current / window, 2), "previous_avg": round(previous / window, 2)}
    if previous < config.MIN_GROWTH_BASELINE:
        return {"pct": None, "direction": None, "reason": "low_volume", **averages}
    pct = round((current - previous) / previous * 100, 1)
    return {"pct": pct, "direction": "up" if pct > 0 else "down" if pct < 0 else "flat", "reason": None, **averages}


def _snapshot_rows(db, context, kind):
    return db.query("""SELECT stat_key, active_count, new_count, salary_median, salary_p25, salary_p75, salary_count
                       FROM market_daily_stats WHERE snapshot_date = ? AND market = ? AND kind = ?""",
                    (context["snapshot_date"], context["market"], kind))


def _read(market, build):
    ensure_fresh()
    with storage.connection() as db:
        context = _context(db, market)
        return {**context, **(build(db, context) if context["status"] == "ready" else {})}


def overview(market):
    def build(db, context):
        total = _snapshot_rows(db, context, "total")[0]
        meta = {row["stat_key"]: row["active_count"] for row in _snapshot_rows(db, context, "meta")}
        week = _complete_days(context, 7)
        series = _new_counts(db, market, "total", week[0] if week else _day(context["snapshot_date"])).get("listings", {})
        daily = [{"date": day.isoformat(), "count": series.get(day.isoformat(), 0)} for day in week]
        active = {row["market"]: row["active_count"] for row in db.query(
            "SELECT market, active_count FROM market_daily_stats WHERE snapshot_date = ? AND kind = 'total'",
            (context["snapshot_date"],))}
        return {
            "totals": {"active_listings": total["active_count"], "companies": meta.get("companies", 0),
                       "tracked_career_listings": meta.get("tracked", 0), "remote_listings": meta.get("remote", 0),
                       "listings_with_salary": total["salary_count"] or 0},
            "activity": {"latest_day": daily[-1] if daily else None, "previous_day": daily[-2] if len(daily) > 1 else None,
                         "new_postings": sum(point["count"] for point in daily), "window_days": len(daily),
                         "daily_average": round(sum(point["count"] for point in daily) / len(daily), 1) if daily else None,
                         "new_today_so_far": total["new_count"]},
            "markets": [{"market": key, "label": value["label"], "active_listings": active.get(key, 0)}
                        for key, value in config.MARKETS.items()],
            "growth": _growth_readiness(db, context),
        }

    result = _read(market, build)
    with storage.connection() as db:
        runs = db.query("""SELECT sources, listings, duplicates, status FROM market_refresh_runs
                           WHERE status IN ('ok', 'partial') ORDER BY started_at DESC LIMIT 1""")
    statuses = {status["source"]: status for status in json.loads(runs[0]["sources"])} if runs else {}
    result["sources"] = [{"source": key, **details, "ok": statuses.get(key, {}).get("ok", False),
                          "partial": statuses.get(key, {}).get("partial", False),
                          "fetched": statuses.get(key, {}).get("fetched", 0),
                          "configured": True,
                          "error": statuses.get(key, {}).get("error")} for key, details in sources.SOURCES.items()]
    result["collection"] = ({"status": runs[0]["status"], "unique_listings": runs[0]["listings"],
                             "duplicates_removed": runs[0]["duplicates"]} if runs else None)
    result["storage"] = storage.engine()
    result["refresh_interval_hours"] = config.refresh_hours()
    return result


def trending(market, limit=10):
    def build(db, context):
        readiness = _growth_readiness(db, context)
        days = _complete_days(context, 2 * config.GROWTH_WINDOW_DAYS)
        counts = _new_counts(db, market, "career", days[0]) if days else {}
        week = [day.isoformat() for day in days[-config.GROWTH_WINDOW_DAYS:]]
        rows = sorted(_snapshot_rows(db, context, "career"), key=lambda row: (-row["active_count"], row["stat_key"]))
        tracked = sum(row["active_count"] for row in rows) or 1
        careers = [{
            "rank": rank, "career": row["stat_key"], "active_listings": row["active_count"],
            "share_pct": round(row["active_count"] / tracked * 100, 1),
            "new_postings": sum(counts.get(row["stat_key"], {}).get(day, 0) for day in week),
            "growth": _growth(counts.get(row["stat_key"], {}), context, readiness),
            "trend": [{"date": day.isoformat(), "new_postings": counts.get(row["stat_key"], {}).get(day.isoformat(), 0)}
                      for day in days],
        } for rank, row in enumerate((row for row in rows if row["active_count"] > 0), start=1)]
        return {"careers": careers[:limit], "tracked_careers": len(careers), "window_days": len(week), "growth": readiness}

    return _read(market, build)


def salary_insights(market):
    def build(db, context):
        rows = [row for row in _snapshot_rows(db, context, "career") if row["salary_count"]]
        enough = [row for row in rows if row["salary_count"] >= config.MIN_SALARY_SAMPLE]
        total = _snapshot_rows(db, context, "total")[0]
        shape = lambda row: {"median": row["salary_median"], "p25": row["salary_p25"], "p75": row["salary_p75"],
                             "sample_size": row["salary_count"]}
        return {
            "currency": "USD", "basis": SALARY_BASIS, "min_sample": config.MIN_SALARY_SAMPLE,
            "overall": shape(total) if (total["salary_count"] or 0) >= config.MIN_SALARY_SAMPLE else None,
            "listings_with_salary": total["salary_count"] or 0, "active_listings": total["active_count"],
            "careers": [{"career": row["stat_key"], **shape(row)}
                        for row in sorted(enough, key=lambda row: -row["salary_median"])],
            "insufficient": [{"career": row["stat_key"], "sample_size": row["salary_count"]}
                             for row in sorted(rows, key=lambda row: -row["salary_count"]) if row not in enough],
        }

    return _read(market, build)


def skill_demand(market, limit=15):
    def build(db, context):
        meta = {row["stat_key"]: row["active_count"] for row in _snapshot_rows(db, context, "meta")}
        base = meta.get("with_skills", 0)
        rows = sorted(_snapshot_rows(db, context, "skill"), key=lambda row: (-row["active_count"], row["stat_key"]))
        return {
            "listings_with_skills": base,
            "active_listings": _snapshot_rows(db, context, "total")[0]["active_count"],
            "skills": [{"rank": rank, "skill": row["stat_key"], "listings": row["active_count"],
                        "share_pct": round(row["active_count"] / base * 100, 1) if base else None}
                       for rank, row in enumerate(rows[:limit], start=1)],
        }

    return _read(market, build)


def history(market, interval="daily", days=30, career=None):
    if career is not None and career not in CAREERS:
        raise ValueError(f"Unknown career: {career}")

    def build(db, context):
        latest, first = _day(context["snapshot_date"]), _day(context["collection_started"])
        start = max(_series_start(context), latest - timedelta(days=days - 1))
        kind, key = ("career", career) if career else ("total", "listings")
        stats = {row["snapshot_date"]: row for row in db.query(
            """SELECT snapshot_date, active_count, new_count FROM market_daily_stats
               WHERE market = ? AND kind = ? AND stat_key = ? AND snapshot_date >= ?""",
            (market, kind, key, start.isoformat()))}
        snapshot_days = {row["snapshot_date"] for row in db.query(
            """SELECT DISTINCT snapshot_date FROM market_daily_stats
               WHERE kind = 'total' AND active_count IS NOT NULL AND snapshot_date >= ?""", (start.isoformat(),))}
        daily = []
        for offset in range((latest - start).days + 1):
            day = start + timedelta(days=offset)
            row = stats.get(day.isoformat())
            snapshotted = day.isoformat() in snapshot_days
            daily.append({
                "date": day.isoformat(), "new_postings": row["new_count"] if row else 0,
                # A career with no open listings has no row on a snapshot day: that is a real zero.
                "active_listings": (row["active_count"] if row and row["active_count"] is not None else 0) if snapshotted else None,
                "backfilled": day < first, "partial": day == latest,
            })
        points = daily
        if interval == "weekly":
            weeks = defaultdict(list)
            for point in daily:
                day = _day(point["date"])
                weeks[day - timedelta(days=day.weekday())].append(point)
            points = [{"week_start": monday.isoformat(), "new_postings": sum(p["new_postings"] for p in items),
                       "days": len(items), "partial": len(items) < 7 or any(p["partial"] for p in items),
                       "backfilled": any(p["backfilled"] for p in items)}
                      for monday, items in sorted(weeks.items())]
        return {"interval": interval, "career": career, "series_start": start.isoformat(), "points": points}

    return _read(market, build)
