"""Fetch component profiles over HTTP and run the unchanged exported matcher."""
import asyncio
import logging
import math
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from .job_matching_training_output import inference
from .schemas import SoftProfile, TechnicalProfile

logger = logging.getLogger(__name__)
_inference_lock = Lock()


def _load_matcher():
    model = inference.load_saved_matcher(Path(inference.__file__).parent)
    model.set_params(device="cpu", n_jobs=1)


@asynccontextmanager
async def career_lifespan(app):
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    default_base_url = f"http://127.0.0.1:{os.getenv('PORT', '8000')}"
    base_url = os.getenv("CAREER_UPSTREAM_BASE_URL", default_base_url).rstrip("/")
    timeout = float(os.getenv("CAREER_UPSTREAM_TIMEOUT_SECONDS", "10"))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("CAREER_UPSTREAM_TIMEOUT_SECONDS must be positive")
    await run_in_threadpool(_load_matcher)
    async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(timeout), trust_env=False) as client:
        app.state.career_client = client
        yield


async def _fetch(client, path):
    try:
        response = await client.get(path)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(504, f"Upstream profile API timed out: {path}") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Upstream profile API {path} returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise HTTPException(502, f"Cannot reach upstream profile API: {path}") from exc
    except ValueError as exc:
        raise HTTPException(502, f"Upstream profile API returned invalid JSON: {path}") from exc
    return data


def _predict(soft_input, technical_input):
    # Serialize access to the shared exported model/explainer; keep CPU work off the event loop.
    with _inference_lock:
        result, _ = inference.recommend_jobs(soft_input, technical_input, n_alternatives=4)
    if len(result["alternative_jobs"]) != 4:
        raise RuntimeError("The exported matcher must return five ranked jobs")
    return result


async def recommend(request: Request):
    technical_input, soft_input = await asyncio.gather(
        _fetch(request.app.state.career_client, "/api/skill/profile"),
        _fetch(request.app.state.career_client, "/api/personality/profile"),
    )
    try:
        technical = TechnicalProfile.model_validate(technical_input)
        soft = SoftProfile.model_validate(soft_input)
        if technical.candidate_id != soft.candidate_id:
            raise ValueError("Upstream profiles must have matching candidate IDs")
        # Pass the original dictionaries; exported parsing retains alias/duplicate validation.
        return await run_in_threadpool(_predict, soft_input, technical_input)
    except ValidationError as exc:
        raise HTTPException(502, "Invalid upstream profile: schema_version must be 1.0, candidate_id and skill names must be nonempty, and levels must be numbers from 0 to 5") from exc
    except ValueError as exc:
        raise HTTPException(502, f"Invalid upstream profile: {exc}") from exc
    except Exception as exc:
        logger.exception("Career inference failed")
        raise HTTPException(500, "Career inference failed; check backend logs") from exc


def metadata(result):
    return {key: value for key, value in result.items() if key not in {"best_job", "alternative_jobs"}}
