# Career Market Pulse

Live job-market statistics for the **Home page** (the section under the CV upload). This is a
Home page feature, not a research component: it has no page, route or sidebar entry of its own
and does not read or change Components 01-04, their models, authentication or CV upload.

| Where | What |
| --- | --- |
| `backend/app/market_pulse/` | collection, storage and the `/api/market/*` routes |
| `frontend/src/pages/home/` | the `MarketPulse` section, its styles and API helpers |
| `backend/app/main.py` | one `include_router` line |
| `frontend/src/pages/Home.jsx` | one `<MarketPulse />` line |

## Endpoints

All take `?market=global|remote|sri_lanka` and return `status` (`ready`, `collecting` or
`unavailable`), `snapshot_date`, `last_updated`, `refreshing` and `stale`.

| Endpoint | Returns |
| --- | --- |
| `GET /api/market/overview` | open listings, new-posting activity, per-market totals, source status |
| `GET /api/market/trending?limit=10` | careers ranked by open listings, new postings, growth, 14-day trend |
| `GET /api/market/salary-insights` | median / quartiles of disclosed pay by career |
| `GET /api/market/skill-demand?limit=15` | most requested technical skills |
| `GET /api/market/history?interval=daily\|weekly&days=30&career=` | new postings over time |

## Data sources

| Source | Used for | Notes |
| --- | --- | --- |
| [Arbeitnow](https://www.arbeitnow.com) | global, remote | full public feed, about 7 days deep, Europe-focused |
| [Remote OK](https://remoteok.com) | global, remote, Sri Lanka (worldwide roles) | full public feed |
| [Remotive](https://remotive.com) | global, remote, Sri Lanka (worldwide roles) | small 24-hour-delayed public subset |
| [Himalayas](https://himalayas.app) | Sri Lanka, remote, global | remote roles open to candidates in Sri Lanka |
| [Jobicy](https://jobicy.com) | global, remote, Sri Lanka ("Anywhere" roles) | full public feed of the last 7 days, worldwide, many in the USA |

All five are free and need no API key. The boards require attribution and a link back; the Home
page lists them with links. Job descriptions are scanned for skills and then discarded, never
stored or republished.

No connected source publishes on-site Sri Lankan vacancies, so the Sri Lanka market is "remote
roles open to candidates in Sri Lanka" and is labelled that way.

## How the numbers are produced

- **Listings** are normalised and deduplicated by title + company (+ location for on-site roles).
- **Careers** come from job-title rules in `taxonomy.py` (English and German). Titles that match
  no rule count towards totals only.
- **Open listings**: listings a source returned within the last 48 hours.
- **New postings per day**: stored listings by posting date. Days before collection started are
  limited to the previous 6 days and flagged `backfilled`; the latest day is flagged `partial`.
- **Growth**: average daily new postings of the latest 7 complete days against the previous 7.
  It is `null` until 14 days have been collected with no gap longer than 6 days, and `null` for a
  career with fewer than 5 postings in the previous week. No percentage is ever estimated.
- **Salaries**: yearly USD pay as disclosed (monthly x12). Hourly and per-task rates, other
  currencies and salaries with no stated period are excluded. A career needs 5 salaries for a median.

## Storage

Three tables, created on first use: `market_listings`, `market_daily_stats` (the daily
snapshots) and `market_refresh_runs`. They live in the shared PostgreSQL database when
`DATABASE_URL` (or `MARKET_DATABASE_URL`) holds real credentials, otherwise in
`.data/market.sqlite3`, the same fallback the other modules use. Existing tables are not touched.

## Refreshing

Reading any endpoint starts a background collection when the stored data is older than
`MARKET_REFRESH_HOURS` (default 12); the first one takes a few minutes. For a snapshot on days
when nobody opens the Home page, schedule:

```bash
cd backend
python -m app.market_pulse.refresh
```

## Tests

```bash
cd backend && python -m unittest tests.market_pulse.test_market_pulse -v
cd frontend && node --test src/pages/home/marketApi.test.js
cd frontend && npx playwright test home-market-pulse
```

No test contacts a job board.
