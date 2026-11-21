"""Career Market Pulse REST APIs for the Home page (see them at /docs).

  GET /api/market/overview         -> totals, market activity, data sources and freshness
  GET /api/market/trending         -> ranked careers with new postings and growth
  GET /api/market/salary-insights  -> median disclosed salary by career
  GET /api/market/skill-demand     -> most requested technical skills
  GET /api/market/history          -> daily or weekly new-posting history
Every endpoint takes ?market=global|remote|sri_lanka; the three markets are never mixed.
Responses always carry status (ready | collecting | unavailable), snapshot_date and last_updated.
Reading these endpoints starts a background collection when the stored data is out of date.
"""
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from . import service
from .storage import StorageError

router = APIRouter(prefix="/api/market", tags=["Career Market Pulse"])
Market = Literal["global", "remote", "sri_lanka"]


def _serve(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except StorageError as exc:
        raise HTTPException(503, f"Market data storage is unavailable. {exc}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/overview", summary="Market totals, activity, data sources and last-updated time")
def overview(market: Market = "global"):
    return _serve(service.overview, market)


@router.get("/trending", summary="Careers ranked by open listings, with new postings and growth")
def trending(market: Market = "global", limit: int = Query(default=10, ge=1, le=50)):
    return _serve(service.trending, market, limit)


@router.get("/salary-insights", summary="Median disclosed salary by career")
def salary_insights(market: Market = "global"):
    return _serve(service.salary_insights, market)


@router.get("/skill-demand", summary="Most requested technical skills")
def skill_demand(market: Market = "global", limit: int = Query(default=15, ge=1, le=60)):
    return _serve(service.skill_demand, market, limit)


@router.get("/history", summary="Daily or weekly history of new postings",
            description="Days before collection started are marked backfilled; the latest day is marked partial.")
def history(market: Market = "global", interval: Literal["daily", "weekly"] = "daily",
            days: int = Query(default=30, ge=7, le=180), career: str | None = Query(default=None, min_length=1)):
    return _serve(service.history, market, interval, days, career)
