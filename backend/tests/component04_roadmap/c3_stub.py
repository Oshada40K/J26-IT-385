# Owner: Dewmi - Component 04.
"""Stub Component 03 provider for C4 tests: replaces c3_link._call_c03 (the only place C4 calls C03), so unit tests
never load or run the real C03 model. It returns the same shape as app.component03_career.service.recommend and
records every call (candidate_id and forwarded Authorization header)."""
from unittest.mock import patch

from app.component04_roadmap import c3_link

# Real O*NET 30.0 codes and titles from C03's catalogue (preprocessing_catalogue.json).
SOFTWARE_DEVELOPERS = ("15-1252.00", "Software Developers")
WEB_DEVELOPERS = ("15-1254.00", "Web Developers")
PROGRAMMERS = ("15-1251.00", "Computer Programmers")
QA_TESTERS = ("15-1253.00", "Software Quality Assurance Analysts and Testers")
SYSTEMS_ARCHITECTS = ("15-1299.08", "Computer Systems Engineers/Architects")
SYSTEMS_ANALYSTS = ("15-1211.00", "Computer Systems Analysts")
# In C03 (889 occupations) but not among C4's 32 IT careers.
CHIEF_EXECUTIVES = ("11-1011.00", "Chief Executives")
OPERATIONS_RESEARCH = ("15-2031.00", "Operations Research Analysts")
STATISTICIANS = ("15-2041.00", "Statisticians")
DATA_ENTRY = ("43-9021.00", "Data Entry Keyers")
GRAPHIC_DESIGNERS = ("27-1024.00", "Graphic Designers")

DEFAULT_JOBS = [SOFTWARE_DEVELOPERS, WEB_DEVELOPERS, PROGRAMMERS, QA_TESTERS, SYSTEMS_ARCHITECTS]
UNSUPPORTED_TOP1 = [CHIEF_EXECUTIVES, WEB_DEVELOPERS, SOFTWARE_DEVELOPERS, PROGRAMMERS, QA_TESTERS]
NONE_SUPPORTED = [CHIEF_EXECUTIVES, OPERATIONS_RESEARCH, STATISTICIANS, DATA_ENTRY, GRAPHIC_DESIGNERS]


def c3_result(candidate_id, jobs, scores=None):
    """Same top-level shape as C03 service.recommend (only the fields C4 reads, plus C03's metadata)."""
    scores = scores or [round(80 - 3.5 * i, 2) for i in range(len(jobs))]
    records = [{"rank": i + 1, "recommendation": "Best match" if i == 0 else f"Alternative {i}",
                "onet_soc_code": code, "job_title": title, "match_score_0_to_100": scores[i]}
               for i, (code, title) in enumerate(jobs)]
    return {"candidate_id": candidate_id, "onet_version": "30.0",
            "model_type": "XGBRegressor trained on synthetic O*NET-derived pseudo-labels",
            "score_meaning": "Prototype skill-evidence match score; not a hiring probability or validated suitability score",
            "eligible_occupations": 889, "unrecognised_skills": [],
            "best_job": records[0], "alternative_jobs": records[1:]}


class StubC03:
    """Set .jobs to change the recommendation, or .error to an exception (e.g. HTTPException(502)) to make C03 fail."""

    def __init__(self, jobs=None):
        self.jobs = list(jobs or DEFAULT_JOBS)
        self.scores = None
        self.error = None
        self.calls = []

    async def __call__(self, request, candidate_id):
        self.calls.append({"candidate_id": candidate_id, "authorization": request.headers.get("authorization")})
        if self.error:
            raise self.error
        return c3_result(candidate_id, self.jobs, self.scores)

    def start(self):
        self._patch = patch.object(c3_link, "_call_c03", self)
        self._patch.start()
        return self

    def stop(self):
        self._patch.stop()
