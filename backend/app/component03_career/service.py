"""Fetch component profiles over HTTP and run the unchanged exported matcher."""
import asyncio
import logging
import math
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from urllib.parse import quote, urlsplit

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from .job_matching_training_output import inference
from .schemas import SoftProfile
from .profile_adapter import adapt_technical_profile

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


async def _fetch(client, path, headers=None):
    try:
        response = await client.get(path, headers=headers)
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


async def recommend(request: Request, candidate_id: str | None = None):
    technical_path = os.getenv('CAREER_TECHNICAL_PROFILE_PATH',
        '/api/component01/skills/{candidate_id}/details' if candidate_id else '/api/skill/profile')
    soft_path = os.getenv('CAREER_SOFT_PROFILE_PATH', '/api/personality/profile')
    if '{candidate_id}' in technical_path or '{candidate_id}' in soft_path:
        if not candidate_id or not candidate_id.strip():
            raise HTTPException(422, 'candidate_id is required for candidate profile endpoints')
    encoded_id = quote(candidate_id, safe='') if candidate_id else ''
    technical_path = technical_path.replace('{candidate_id}', encoded_id)
    soft_path = soft_path.replace('{candidate_id}', encoded_id)
    # Credentials belong to this request, never the shared client's defaults.
    headers = {'Authorization': request.headers['authorization']} if 'authorization' in request.headers else {}
    technical_input, soft_input = await asyncio.gather(
        _fetch(request.app.state.career_client, technical_path, headers),
        _fetch(request.app.state.career_client, soft_path, headers),
    )
    try:
        is_assessment = isinstance(technical_input, dict) and 'skills' in technical_input
        technical_input = adapt_technical_profile(technical_input)
        soft = SoftProfile.model_validate(soft_input)
        if candidate_id is not None and technical_input['candidate_id'] != candidate_id:
            raise ValueError('Upstream profile candidate ID does not match the requested candidate')
        if technical_input['candidate_id'] != soft.candidate_id:
            if ((candidate_id is not None or is_assessment)
                    and urlsplit(soft_path).path.rstrip('/') == '/api/personality/profile'):
                # Component 2 currently supplies a fixed sample, as requested.
                # Bind a copy to the live candidate for the matcher's identity
                # contract; preserve every soft-skill value and the API payload.
                soft_input = {**soft_input, 'candidate_id': technical_input['candidate_id']}
            else:
                raise ValueError("Upstream profiles must have matching candidate IDs")
        return await run_in_threadpool(_predict, soft_input, technical_input)
    except ValidationError as exc:
        raise HTTPException(502, "Invalid upstream profile: expected a completed cv_evidence_rubric_v1 assessment (levels 1 to 5) or schema_version 1.0 profiles (levels 0 to 5), with nonempty candidate IDs and skill names") from exc
    except ValueError as exc:
        raise HTTPException(502, f"Invalid upstream profile: {exc}") from exc
    except Exception as exc:
        logger.exception("Career inference failed")
        raise HTTPException(500, "Career inference failed; check backend logs") from exc


def metadata(result):
    return {key: value for key, value in result.items() if key not in {"best_job", "alternative_jobs"}}
