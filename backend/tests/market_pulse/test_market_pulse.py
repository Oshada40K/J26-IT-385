"""Career Market Pulse: classification, source normalisation, snapshots, growth and the REST API.

No test touches the network: job boards are replaced by httpx mock transports or by patching
sources.collect, and time is controlled by patching service.now. Storage is a temporary SQLite file.
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.market_pulse import config, service, sources, storage
from app.market_pulse.router import router
from app.market_pulse.taxonomy import classify_career, extract_skills

DAY0 = datetime(2026, 3, 2, tzinfo=timezone.utc)  # a Monday


def listing(title, company, posted, *, remote=False, sri_lanka=False, salary=None, description="", location="Berlin"):
    return sources._listing("test", f"{title}-{company}", "https://example.test/job", title, company, location, posted,
                            remote=remote, sri_lanka=sri_lanka, salary_usd=salary, description=description)


def ok_status(count):
    return [{"source": "arbeitnow", "ok": True, "partial": False, "fetched": count, "error": None}]


class TaxonomyTests(unittest.TestCase):
    def test_titles_map_to_tracked_careers(self):
        cases = {
            "Senior Machine Learning Engineer, LLM Inference": "Machine Learning / AI Engineer",
            "Data Scientist H/F - Paris": "Data Scientist",
            "Senior Data Engineer (m/w/d)": "Data Engineer",
            "Junior Business Data Analyst": "Data Analyst",
            "Senior Site Reliability Engineer": "DevOps / Site Reliability Engineer",
            "Fullstack Developer (Java, Angular)": "Full Stack Developer",
            "Senior Java Entwickler (m/w/d)": "Backend Developer",
            "React Native Developer": "Mobile Developer",
            "Softwareentwickler (m/w/d)": "Software Engineer",
            "Senior Software Engineer, Roku UI": "Software Engineer",
            "UX/UI Designer": "UI/UX Designer",
            "IT-Systemadministrator (m/w/d)": "Systems / Network Administrator",
            "SAP FI Berater (m/w/d)": "ERP / CRM Consultant",
            "Senior Cyber Security Specialist": "Cybersecurity Specialist",
        }
        for title, career in cases.items():
            self.assertEqual(classify_career(title), career, title)

    def test_non_technology_titles_stay_unclassified(self):
        for title in ("Business Development Manager (London)", "Sales Development Representative DACH",
                      "Kundenberater (m/w/d)", "Teamlead Electrical Engineering (m/w/d)", "Personalentwickler (m/w/d)", ""):
            self.assertIsNone(classify_career(title), title)

    def test_skills_are_whole_tokens_and_ambiguous_words_need_their_capital(self):
        text = "Java, JavaScript, MySQL and T-SQL; C#, C++ and ASP.NET. You react quickly and excel at Go to market."
        self.assertEqual(extract_skills(text), [".NET", "C#", "C++", "Java", "JavaScript", "MySQL", "SQL"])
        self.assertEqual(extract_skills("React, Excel, Golang, k8s, <b>Python</b>"), ["Excel", "Golang", "Kubernetes", "Python", "React"])
        self.assertEqual(extract_skills("Javanese coffee, scalable postgresql"), ["PostgreSQL"])


class SalaryTests(unittest.TestCase):
    def test_only_trustworthy_annual_usd_pay_is_used(self):
        self.assertEqual(sources.annual_usd(100000, 140000), 120000)
        self.assertEqual(sources.annual_usd(5000, 7000, "USD", "monthly"), 72000)
        self.assertIsNone(sources.annual_usd(45, 90, "USD", "hourly"))        # contract rate, not a salary
        self.assertIsNone(sources.annual_usd(60000, 80000, "EUR", "annual"))  # no currency conversion
        self.assertIsNone(sources.annual_usd(0, 0))
        self.assertIsNone(sources.annual_usd(114000000, 140000000))           # outside the plausible band
        self.assertIsNone(sources.annual_usd("n/a", None))

    def test_free_text_salaries_must_be_clearly_yearly_usd(self):
        self.assertEqual(sources.parse_usd_salary("$170k - $200k"), 185000)
        self.assertEqual(sources.parse_usd_salary("$120,000 - $150,000"), 135000)
        for text in ("$14 - $20/hour", "$3.5k-$5k/month", "$1000 per task", "70K-80K", "$35,3k- $52k", "", None):
            self.assertIsNone(sources.parse_usd_salary(text), text)


class SourceTests(unittest.TestCase):
    def client(self, handler):
        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_arbeitnow_follows_pagination_and_normalises(self):
        def handler(request):
            page = int(request.url.params["page"])
            job = {"slug": f"job-{page}", "company_name": "Acme &amp; Co", "title": "Senior Python Engineer &#38; Lead",
                   "description": "<p>Python, <b>Docker</b> and AWS</p>", "remote": page == 1, "url": "https://x/job",
                   "tags": ["Kubernetes"], "location": "Berlin", "created_at": 1772445600}
            return httpx.Response(200, json={"data": [job], "links": {"next": "more" if page == 1 else None}})

        with self.client(handler) as client:
            jobs = list(sources.fetch_arbeitnow(client, pause=0))
        self.assertEqual([job["source_id"] for job in jobs], ["job-1", "job-2"])
        first = jobs[0]
        self.assertEqual((first["title"], first["company"]), ("Senior Python Engineer & Lead", "Acme & Co"))
        self.assertEqual(first["career"], "Backend Developer")
        self.assertEqual(first["skills"], ["AWS", "Docker", "Kubernetes", "Python"])
        self.assertEqual((first["is_remote"], jobs[1]["is_remote"], first["is_sri_lanka"]), (True, False, False))
        self.assertEqual(first["posted_at"], datetime(2026, 3, 2, 10, tzinfo=timezone.utc))
        self.assertIsNone(first["salary_usd"])

    def test_remoteok_skips_the_legal_notice_and_flags_worldwide_roles(self):
        payload = [{"legal": "terms"},
                   {"id": "1", "position": "Data Engineer", "company": "A", "location": "Worldwide", "epoch": 1772445600,
                    "salary_min": 90000, "salary_max": 110000, "tags": ["sql"], "url": "u", "description": ""},
                   {"id": "2", "position": "QA Engineer", "company": "B", "location": "New York", "date": "2026-03-02T10:00:00+00:00",
                    "salary_min": 21, "salary_max": 21, "tags": [], "url": "u", "description": ""}]
        with self.client(lambda request: httpx.Response(200, json=payload)) as client:
            jobs = list(sources.fetch_remoteok(client))
        self.assertEqual(len(jobs), 2)
        self.assertEqual((jobs[0]["salary_usd"], jobs[0]["is_sri_lanka"], jobs[0]["is_remote"]), (100000, True, True))
        self.assertEqual((jobs[1]["salary_usd"], jobs[1]["is_sri_lanka"]), (None, False))

    def test_himalayas_listings_are_the_sri_lanka_market(self):
        job = {"title": "Backend Developer", "companyName": "C", "locationRestrictions": [], "categories": ["Developer"],
               "parentCategories": [], "description": "<p>Django</p>", "pubDate": 1772445600, "guid": "g1",
               "applicationLink": "a", "minSalary": 50, "maxSalary": 90, "currency": "USD", "salaryPeriod": "hourly"}
        seen = []

        def handler(request):
            seen.append(dict(request.url.params))
            return httpx.Response(200, json={"jobs": [job], "totalCount": 1})

        with self.client(handler) as client:
            jobs = list(sources.fetch_himalayas(client, pause=0))
        self.assertEqual(seen, [{"country": "LK", "page": "1"}])
        self.assertEqual((jobs[0]["is_sri_lanka"], jobs[0]["is_remote"], jobs[0]["location"]), (True, True, "Worldwide"))
        self.assertIsNone(jobs[0]["salary_usd"])  # hourly rates are never annualised

    def test_jobicy_follows_the_cursor_and_keeps_only_trustworthy_salaries(self):
        def job(job_id, geo, low, high, currency, period):
            return {"id": job_id, "url": f"https://jobicy.com/jobs/{job_id}", "jobTitle": "Senior Data Engineer",
                    "companyName": f"Company {job_id}", "jobGeo": geo, "jobIndustry": ["Data Science &amp; Analytics"],
                    "jobDescription": "<p>Python, SQL and Airflow</p>", "pubDate": "2026-03-02T10:00:00+00:00",
                    "salaryMin": low, "salaryMax": high, "salaryCurrency": currency, "salaryPeriod": period}

        pages = {None: {"jobs": [job(1, "Anywhere", 120000, 140000, "USD", "yearly"), job(2, "USA", 45, 60, "USD", "hourly")],
                        "hasMore": True, "nextCursor": "next-page"},
                 "next-page": {"jobs": [job(3, "Europe", 70000, 90000, "EUR", "yearly"), job(4, "UK", 8000, 8000, "USD", None)],
                               "hasMore": False, "nextCursor": None}}
        seen = []

        def handler(request):
            seen.append(dict(request.url.params))
            return httpx.Response(200, json=pages[request.url.params.get("cursor")])

        with self.client(handler) as client:
            jobs = list(sources.fetch_jobicy(client, pause=0))
        self.assertEqual(seen, [{"count": "100"}, {"count": "100", "cursor": "next-page"}])
        self.assertEqual([j["source_id"] for j in jobs], ["1", "2", "3", "4"])
        # Yearly USD kept; hourly, EUR and a salary with no stated period are excluded.
        self.assertEqual([j["salary_usd"] for j in jobs], [130000, None, None, None])
        self.assertEqual([j["is_sri_lanka"] for j in jobs], [True, False, False, False])   # only "Anywhere" roles
        self.assertTrue(all(j["is_remote"] for j in jobs))
        self.assertEqual((jobs[0]["career"], jobs[0]["skills"]), ("Data Engineer", ["Airflow", "Python", "SQL"]))

    def test_error_messages_leave_out_query_strings(self):
        real_client = httpx.Client
        failing = lambda **kwargs: real_client(transport=httpx.MockTransport(lambda request: httpx.Response(401)))
        with patch.object(sources.httpx, "Client", failing), patch.object(sources.time, "sleep", lambda seconds: None):
            _, status = sources._run("jobicy")
        self.assertEqual((status["ok"], status["fetched"]), (False, 0))
        self.assertIn("401", status["error"])
        self.assertNotIn("count=100", status["error"])

    def test_a_failing_board_keeps_earlier_pages_and_is_marked_partial(self):
        def handler(request):
            if request.url.params["page"] == "2":
                return httpx.Response(404)
            job = {"slug": "a", "company_name": "A", "title": "DevOps Engineer", "description": "", "remote": False,
                   "url": "u", "tags": [], "location": "Bonn", "created_at": 1772445600}
            return httpx.Response(200, json={"data": [job], "links": {"next": "more"}})

        real_client = httpx.Client
        with patch.object(sources.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler))), \
                patch.object(sources.time, "sleep", lambda seconds: None):
            jobs, status = sources._run("arbeitnow")
        self.assertEqual(len(jobs), 1)
        self.assertEqual((status["ok"], status["partial"], status["fetched"]), (True, True, 1))

    def test_every_source_is_collected_and_reported(self):
        with patch.dict(sources.FETCHERS, {name: (lambda client: iter(())) for name in sources.FETCHERS}):
            _, statuses = sources.collect()
        self.assertEqual([status["source"] for status in statuses], ["arbeitnow", "remoteok", "remotive", "himalayas", "jobicy"])
        self.assertEqual(set(sources.SOURCES), set(sources.FETCHERS))


class MarketCase(unittest.TestCase):
    """Temporary database, no automatic refresh, controllable clock and job feed."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"MARKET_DATABASE_PATH": str(Path(self.temp.name) / "market.sqlite3"),
                                           "MARKET_AUTO_REFRESH": "false", "DATABASE_URL": "", "MARKET_DATABASE_URL": ""})
        self.env.start()
        self.clock = DAY0

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def collect(self, day, listings, hour=23, statuses=None):
        """Runs one refresh as if it happened on DAY0 + day, with the feed returning `listings`."""
        self.clock = DAY0 + timedelta(days=day, hours=hour)
        with patch.object(service, "now", lambda: self.clock), \
                patch.object(service.sources, "collect", lambda: (listings, statuses or ok_status(len(listings)))):
            return service.refresh()

    def read(self, call, *args):
        with patch.object(service, "now", lambda: self.clock):
            return call(*args)

    def postings(self, day, title, count, **kwargs):
        posted = DAY0 + timedelta(days=day, hours=10)
        return [listing(title, f"{title} Co day{day} no{index}", posted, **kwargs) for index in range(count)]


class SnapshotTests(MarketCase):
    def test_duplicates_are_merged_across_sources(self):
        posted = DAY0 + timedelta(hours=9)
        same = [listing("Data Engineer (m/w/d)", "Acme", posted, remote=True, location="Berlin"),
                listing("Data Engineer", "ACME", posted - timedelta(days=1), remote=True, sri_lanka=True, salary=90000, location="Worldwide")]
        onsite = [listing("Data Engineer", "Acme", posted, location="Berlin"), listing("Data Engineer", "Acme", posted, location="Hamburg")]
        unique, removed = service.dedupe(same + onsite)
        self.assertEqual((len(unique), removed), (3, 1))  # the remote pair merges; two cities are two openings
        merged = unique[service.listing_key(same[0])]
        self.assertEqual((merged["is_sri_lanka"], merged["salary_usd"], merged["posted_at"]), (True, 90000, posted - timedelta(days=1)))

    def test_no_data_is_reported_as_unavailable_not_as_zeros(self):
        for call in (service.overview, service.trending, service.salary_insights, service.skill_demand, service.history):
            result = self.read(call, "global")
            self.assertEqual((result["status"], result["snapshot_date"], result["last_updated"]), ("unavailable", None, None))
            for absent in ("totals", "careers", "skills", "points"):
                self.assertNotIn(absent, result)

    def test_a_failed_collection_stores_no_snapshot_and_explains_why(self):
        failed = [{"source": "arbeitnow", "ok": False, "partial": False, "fetched": 0, "error": "ConnectError: offline"}]
        summary = self.collect(0, [], statuses=failed)
        self.assertEqual(summary["status"], "failed")
        result = self.read(service.overview, "global")
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("No source returned any listings", result["message"])

    def test_markets_are_kept_separate(self):
        feed = (self.postings(0, "Software Engineer", 4) + self.postings(0, "Data Analyst", 3, remote=True, location="Remote")
                + self.postings(0, "Backend Developer", 2, remote=True, sri_lanka=True, location="Worldwide")
                + self.postings(0, "Kundenberater", 5))
        summary = self.collect(0, feed)
        self.assertEqual((summary["status"], summary["listings"]), ("ok", 14))
        totals = {market: self.read(service.overview, market)["totals"] for market in config.MARKETS}
        self.assertEqual([totals[m]["active_listings"] for m in ("global", "remote", "sri_lanka")], [14, 5, 2])
        self.assertEqual([totals[m]["tracked_career_listings"] for m in ("global", "remote", "sri_lanka")], [9, 5, 2])
        self.assertEqual(totals["global"]["remote_listings"], 5)
        ranked = lambda market: [(c["rank"], c["career"], c["active_listings"]) for c in self.read(service.trending, market)["careers"]]
        self.assertEqual(ranked("global"), [(1, "Software Engineer", 4), (2, "Data Analyst", 3), (3, "Backend Developer", 2)])
        self.assertEqual(ranked("remote"), [(1, "Data Analyst", 3), (2, "Backend Developer", 2)])
        self.assertEqual(ranked("sri_lanka"), [(1, "Backend Developer", 2)])
        overview = self.read(service.overview, "sri_lanka")
        self.assertEqual([(m["market"], m["active_listings"]) for m in overview["markets"]], [("global", 14), ("remote", 5), ("sri_lanka", 2)])
        self.assertEqual(overview["collection"], {"status": "ok", "unique_listings": 14, "duplicates_removed": 0})
        self.assertEqual(overview["storage"], "sqlite")
        self.assertEqual([source["source"] for source in overview["sources"]], ["arbeitnow", "remoteok", "remotive", "himalayas", "jobicy"])

    def test_skill_demand_and_salary_medians_need_enough_listings(self):
        feed = (self.postings(0, "Data Engineer", 5, salary=None, description="Python and SQL")
                + self.postings(0, "Backend Developer", 3, description="Python"))
        for index, pay in enumerate((80000, 90000, 100000, 110000, 120000)):
            feed[index]["salary_usd"] = pay
        feed[5]["salary_usd"] = 70000
        self.collect(0, feed)
        skills = self.read(service.skill_demand, "global")
        self.assertEqual(skills["listings_with_skills"], 8)
        self.assertEqual([(s["skill"], s["listings"], s["share_pct"]) for s in skills["skills"]], [("Python", 8, 100.0), ("SQL", 5, 62.5)])
        salary = self.read(service.salary_insights, "global")
        self.assertEqual(salary["careers"], [{"career": "Data Engineer", "median": 100000, "p25": 90000, "p75": 110000, "sample_size": 5}])
        self.assertEqual(salary["insufficient"], [{"career": "Backend Developer", "sample_size": 1}])  # never a median of one
        self.assertEqual((salary["overall"]["median"], salary["overall"]["sample_size"], salary["currency"]), (95000, 6, "USD"))

    def test_listings_stay_open_only_while_a_source_still_returns_them(self):
        old = self.postings(0, "Software Engineer", 3)
        self.collect(0, old)
        self.collect(1, old[:1] + self.postings(1, "Data Scientist", 2))
        self.assertEqual(self.read(service.overview, "global")["totals"]["active_listings"], 5)   # all seen within 48 hours
        self.collect(4, old[:1])
        self.assertEqual(self.read(service.overview, "global")["totals"]["active_listings"], 1)
        with storage.connection() as db:  # history is kept for posting counts
            self.assertEqual(db.query("SELECT COUNT(*) AS n FROM market_listings")[0]["n"], 5)


class GrowthTests(MarketCase):
    def run_days(self, days, plan):
        for day in days:
            feed = [item for title, count in plan(day).items() for item in self.postings(day, title, count)]
            self.collect(day, feed)

    @staticmethod
    def plan(day):
        return {"Software Engineer": 2 if day < 7 else 3,   # 2 a day, then 3 a day: +50%
                "Data Analyst": 1 if day < 7 else 0,          # 7 last week, none this week: -100%
                "Data Scientist": 1 if day in (3, 9) else 0}  # too few postings for a percentage

    def test_growth_is_withheld_until_fourteen_days_are_collected(self):
        self.run_days(range(6), self.plan)
        trending = self.read(service.trending, "global")
        self.assertEqual({key: trending["growth"][key] for key in ("ready", "days_collected", "days_required", "reason")},
                         {"ready": False, "days_collected": 5, "days_required": 14, "reason": "collecting"})
        for career in trending["careers"]:
            self.assertEqual(career["growth"], {"pct": None, "direction": None, "reason": "collecting"})
        self.assertFalse(self.read(service.overview, "global")["growth"]["ready"])

    def test_growth_compares_the_latest_week_with_the_previous_week(self):
        self.run_days(range(15), self.plan)   # the snapshot on day 14 compares days 7-13 with days 0-6
        trending = self.read(service.trending, "global", 50)
        self.assertTrue(trending["growth"]["ready"])
        growth = {career["career"]: career["growth"] for career in trending["careers"]}
        self.assertEqual(growth["Software Engineer"], {"pct": 50.0, "direction": "up", "reason": None, "current_avg": 3.0, "previous_avg": 2.0})
        engineer = next(career for career in trending["careers"] if career["career"] == "Software Engineer")
        self.assertEqual((engineer["new_postings"], trending["window_days"]), (21, 7))
        self.assertEqual([point["new_postings"] for point in engineer["trend"]], [2] * 7 + [3] * 7)
        # Data Analyst has no open listing any more, so it is not ranked; its decline shows in its history.
        self.assertNotIn("Data Analyst", growth)
        analyst = self.read(service.history, "global", "weekly", 30, "Data Analyst")
        self.assertEqual([(week["week_start"], week["new_postings"]) for week in analyst["points"]][-3:],
                         [("2026-03-02", 7), ("2026-03-09", 0), ("2026-03-16", 0)])

    def test_a_declining_and_a_low_volume_career(self):
        def plan(day):
            return {"Data Analyst": 2 if day < 7 else 1, "Data Scientist": 1 if day in (3, 9, 14) else 0}
        self.run_days(range(15), plan)
        growth = {career["career"]: career["growth"] for career in self.read(service.trending, "global", 50)["careers"]}
        self.assertEqual((growth["Data Analyst"]["pct"], growth["Data Analyst"]["direction"]), (-50.0, "down"))
        self.assertEqual((growth["Data Scientist"]["pct"], growth["Data Scientist"]["reason"]), (None, "low_volume"))

    def test_a_long_collection_gap_pauses_growth(self):
        self.run_days([0, 1, 2, 12, 13, 14], self.plan)
        growth = self.read(service.trending, "global")["growth"]
        self.assertEqual((growth["ready"], growth["reason"]), (False, "gap"))

    def test_history_marks_backfilled_and_partial_days(self):
        early = [item for day in (-8, -3, -1) for item in self.postings(day, "Software Engineer", 2)]
        self.collect(0, early + self.postings(0, "Software Engineer", 1), hour=6)
        self.collect(1, self.postings(1, "Software Engineer", 4))
        daily = self.read(service.history, "global", "daily", 30)
        self.assertEqual((daily["collection_started"], daily["series_start"]), ("2026-03-02", "2026-02-24"))
        points = {point["date"]: point for point in daily["points"]}
        self.assertEqual(list(points)[0], "2026-02-24")   # the posting 8 days earlier is outside the trusted window
        self.assertEqual(points["2026-02-27"], {"date": "2026-02-27", "new_postings": 2, "active_listings": None, "backfilled": True, "partial": False})
        self.assertEqual(points["2026-03-02"], {"date": "2026-03-02", "new_postings": 1, "active_listings": 7, "backfilled": False, "partial": False})
        self.assertEqual(points["2026-03-03"], {"date": "2026-03-03", "new_postings": 4, "active_listings": 11, "backfilled": False, "partial": True})
        weekly = self.read(service.history, "global", "weekly", 30)["points"]
        self.assertEqual([(week["week_start"], week["new_postings"], week["days"], week["partial"]) for week in weekly],
                         [("2026-02-23", 4, 6, True), ("2026-03-02", 5, 2, True)])
        activity = self.read(service.overview, "global")["activity"]
        self.assertEqual((activity["latest_day"], activity["window_days"], activity["new_today_so_far"]),
                         ({"date": "2026-03-02", "count": 1}, 7, 4))

    def test_refresh_is_due_only_when_data_is_old(self):
        with storage.connection() as db:
            self.assertTrue(service._refresh_due(db))
        self.collect(0, self.postings(0, "Software Engineer", 1), hour=1)
        for hours, due in ((2, False), (11, False), (14, True)):
            self.clock = DAY0 + timedelta(hours=hours)
            with storage.connection() as db, patch.object(service, "now", lambda: self.clock):
                self.assertEqual(service._refresh_due(db), due, hours)
        self.assertFalse(self.read(service.overview, "global")["stale"])
        self.clock = DAY0 + timedelta(days=2)
        self.assertTrue(self.read(service.overview, "global")["stale"])

    def test_a_collection_cut_off_by_a_restart_is_started_again(self):
        with storage.connection() as db:
            db.execute("INSERT INTO market_refresh_runs (run_id, started_at, status) VALUES ('cut-off', ?, 'running')",
                       (service.stamp(DAY0),))
        for minutes, due, state in ((5, False, "collecting"), (20, True, "unavailable")):
            self.clock = DAY0 + timedelta(minutes=minutes)
            with storage.connection() as db, patch.object(service, "now", lambda: self.clock):
                self.assertEqual(service._refresh_due(db), due, minutes)
            self.assertEqual(self.read(service.overview, "global")["status"], state, minutes)


class ApiTests(MarketCase):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        super().tearDown()

    def test_endpoints_return_the_stored_statistics(self):
        self.collect(0, self.postings(0, "Software Engineer", 3, description="Python") + self.postings(0, "Data Analyst", 1, remote=True))
        with patch.object(service, "now", lambda: self.clock):
            responses = {path: self.client.get(f"/api/market/{path}", params={"market": "global"})
                         for path in ("overview", "trending", "salary-insights", "skill-demand", "history")}
            remote = self.client.get("/api/market/trending", params={"market": "remote", "limit": 1}).json()
            weekly = self.client.get("/api/market/history", params={"interval": "weekly", "career": "Software Engineer"}).json()
        for path, response in responses.items():
            self.assertEqual(response.status_code, 200, path)
            body = response.json()
            self.assertEqual((body["status"], body["market"], body["snapshot_date"]), ("ready", "global", "2026-03-02"), path)
            self.assertEqual(body["last_updated"], "2026-03-02T23:00:00Z", path)
        self.assertEqual(responses["overview"].json()["totals"]["active_listings"], 4)
        self.assertEqual(responses["skill-demand"].json()["skills"][0]["skill"], "Python")
        self.assertEqual([career["career"] for career in remote["careers"]], ["Data Analyst"])
        self.assertEqual((weekly["interval"], weekly["career"], weekly["points"][-1]["new_postings"]), ("weekly", "Software Engineer", 3))

    def test_invalid_requests_are_rejected(self):
        self.assertEqual(self.client.get("/api/market/overview", params={"market": "mars"}).status_code, 422)
        self.assertEqual(self.client.get("/api/market/trending", params={"limit": 0}).status_code, 422)
        self.assertEqual(self.client.get("/api/market/history", params={"interval": "hourly"}).status_code, 422)
        unknown = self.client.get("/api/market/history", params={"career": "Astronaut"})
        self.assertEqual((unknown.status_code, unknown.json()["detail"]), (422, "Unknown career: Astronaut"))

    def test_storage_problems_are_a_clear_503(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://market:wrong@127.0.0.1:1/none"}):
            self.assertEqual(storage.engine(), "postgresql")
            response = self.client.get("/api/market/overview")
        self.assertEqual(response.status_code, 503)
        self.assertIn("Market data storage is unavailable", response.json()["detail"])
        self.assertNotIn("wrong", response.json()["detail"])

    def test_the_env_example_placeholder_is_not_treated_as_a_database(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://username:password@localhost:5432/career_db"}):
            self.assertIsNone(config.database_url())
            self.assertEqual(self.client.get("/api/market/overview").json()["storage"], "sqlite")


if __name__ == "__main__":
    unittest.main()
