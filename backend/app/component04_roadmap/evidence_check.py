# Owner: Dewmi - Component 04.
"""Simple, safe checks for optional skill proof, run right after upload.

Component 01 is the main verifier. Until it is connected, these checks can only give a capped
PROVISIONAL level:
- github            GitHub REST API: the repository must exist, not be empty and match the skill.
- certificate_link  the URL is never fetched; only its domain is compared with a trusted list.
- certificate_file  cannot be checked automatically, so it stays pending (level 2).
"""
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .errors import EvidenceError

PROVISIONAL_LEVEL_LINK = 3          # out of 5: trusted certificate link or matching GitHub repository
PROVISIONAL_LEVEL_FILE = 2          # out of 5: uploaded certificate file, pending review
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_DESCRIPTION = 500
PROOF_TYPES = ("github", "certificate_link", "certificate_file")
GITHUB_TIMEOUT_SECONDS = 5
GITHUB_REPO_URL = re.compile(r"^https://github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$")
TRUSTED_CERTIFICATE_DOMAINS = (
    "credly.com", "coursera.org", "udemy.com", "linkedin.com/learning", "aws.amazon.com", "learn.microsoft.com",
    "cloud.google.com", "freecodecamp.org", "hackerrank.com", "cisco.com", "oracle.com",
)
# File signature -> allowed extensions (checked on content, not only on the file name).
FILE_SIGNATURES = {b"%PDF": (".pdf",), b"\x89PNG\r\n\x1a\n": (".png",), b"\xff\xd8\xff": (".jpg", ".jpeg")}

# Small keyword map: which GitHub languages / words show a skill. "any": every non-empty repository counts;
# "all": both a language AND a keyword must match. Skills not listed use their own name (see _rule).
SKILL_RULES = {
    "Git": {"any": True},
    "Programming Fundamentals": {"any": True},
    "Java": {"languages": ["Java"]},
    "Spring Boot": {"languages": ["Java", "Kotlin"], "keywords": ["spring"], "all": True},
    "Python": {"languages": ["Python", "Jupyter Notebook"]},
    "JavaScript": {"languages": ["JavaScript", "TypeScript"]},
    "TypeScript": {"languages": ["TypeScript"]},
    "HTML and CSS": {"languages": ["HTML", "CSS", "SCSS"]},
    "React": {"languages": ["JavaScript", "TypeScript"], "keywords": ["react", "next.js", "nextjs"], "all": True},
    "Angular": {"languages": ["TypeScript"], "keywords": ["angular"], "all": True},
    "Node.js": {"languages": ["JavaScript", "TypeScript"], "keywords": ["node", "express", "nestjs"], "all": True},
    "Django": {"languages": ["Python"], "keywords": ["django"], "all": True},
    ".NET": {"languages": ["C#", "F#"], "keywords": [".net", "dotnet", "asp.net"]},
    "C#": {"languages": ["C#"]},
    "C++": {"languages": ["C++"]},
    "C": {"languages": ["C"]},
    "Embedded C": {"languages": ["C"], "keywords": ["embedded", "arduino", "stm32", "firmware"], "all": True},
    "PHP": {"languages": ["PHP"]},
    "Kotlin": {"languages": ["Kotlin"]},
    "R": {"languages": ["R"]},
    "Solidity": {"languages": ["Solidity"]},
    "Verilog and FPGA": {"languages": ["Verilog", "SystemVerilog", "VHDL"]},
    "Object-Oriented Programming": {"languages": ["Java", "C#", "C++", "Python", "Kotlin", "TypeScript"]},
    "Data Structures and Algorithms": {"keywords": ["algorithm", "data structure", "leetcode", "dsa"]},
    "SQL": {"languages": ["TSQL", "PLpgSQL", "PLSQL"], "keywords": ["sql", "mysql", "postgres", "database"]},
    "PostgreSQL": {"languages": ["PLpgSQL"], "keywords": ["postgres"]},
    "MongoDB": {"keywords": ["mongo"]},
    "Bash Scripting": {"languages": ["Shell"], "keywords": ["bash", "shell"]},
    "Linux": {"languages": ["Shell"], "keywords": ["linux"]},
    "Docker": {"languages": ["Dockerfile"], "keywords": ["docker"]},
    "Kubernetes": {"keywords": ["kubernetes", "k8s", "helm"]},
    "Terraform": {"languages": ["HCL"], "keywords": ["terraform"]},
    "CI/CD": {"keywords": ["ci/cd", "github actions", "pipeline", "jenkins", "ci"]},
    "AWS": {"keywords": ["aws", "amazon web services", "lambda", "s3", "ec2"]},
    "Microsoft Azure": {"keywords": ["azure"]},
    "Pandas": {"languages": ["Python", "Jupyter Notebook"], "keywords": ["pandas"], "all": True},
    "NumPy": {"languages": ["Python", "Jupyter Notebook"], "keywords": ["numpy"], "all": True},
    "Machine Learning": {"languages": ["Python", "Jupyter Notebook", "R"],
                         "keywords": ["machine learning", "ml", "scikit", "sklearn", "model"], "all": True},
    "Deep Learning": {"keywords": ["deep learning", "pytorch", "tensorflow", "keras", "neural"]},
    "Natural Language Processing": {"keywords": ["nlp", "natural language", "text classification", "transformers"]},
    "Generative AI and LLMs": {"keywords": ["llm", "gpt", "langchain", "generative", "rag"]},
    "Test Automation": {"keywords": ["test", "automation", "pytest", "junit", "cypress", "playwright"]},
    "Selenium": {"keywords": ["selenium"]},
    "Unity": {"languages": ["C#", "ShaderLab"], "keywords": ["unity"]},
    "REST API Design": {"keywords": ["api", "rest"]},
}


class GitHubUnavailable(RuntimeError):
    pass


def _result(status, level, details):
    return {"status": status, "provisional_level": level, "check_details": details}


# ------------------------------------------------------------------ validation (400 errors)
def validate_submission(proof_type, url, file_name, content, description):
    """Raises EvidenceError with a clear message. Returns the cleaned URL (or None for files)."""
    if proof_type not in PROOF_TYPES:
        raise EvidenceError("proof_type must be github, certificate_link or certificate_file.")
    if description and len(description) > MAX_DESCRIPTION:
        raise EvidenceError(f"The description can be at most {MAX_DESCRIPTION} characters.")
    if proof_type == "certificate_file":
        if content is None:
            raise EvidenceError("Choose a certificate file (PDF, PNG or JPG).")
        if len(content) > MAX_FILE_BYTES:
            raise EvidenceError("The file is larger than 5 MB.")
        if not file_extension(file_name, content):
            raise EvidenceError("Only PDF, PNG or JPG files are accepted.")
        return None
    url = (url or "").strip()
    if not url:
        raise EvidenceError("Enter a link for this proof.")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise EvidenceError("The link must be a full https:// address.")
    if proof_type == "github" and not GITHUB_REPO_URL.match(url):
        raise EvidenceError("Use a GitHub repository link like https://github.com/<owner>/<repo>.")
    return url


def file_extension(file_name, content):
    """The stored extension when the content and the file name agree on PDF/PNG/JPG, otherwise None."""
    suffix = Path(file_name or "").suffix.lower()
    for signature, extensions in FILE_SIGNATURES.items():
        if content.startswith(signature) and suffix in extensions:
            return suffix
    return None


# ------------------------------------------------------------------ checks
def check(proof_type, url, skill_name):
    if proof_type == "github":
        return check_github(url, skill_name)
    if proof_type == "certificate_link":
        return check_certificate_link(url)
    return _result("pending", PROVISIONAL_LEVEL_FILE,
                   "Certificate file received. Files cannot be checked automatically, so it is pending review.")


def check_certificate_link(url):
    """Never fetches the link (security); only compares the domain with the trusted list."""
    domain = trusted_domain(url)
    if domain:
        return _result("provisional", PROVISIONAL_LEVEL_LINK,
                       f"Certificate link from a trusted provider ({domain}). The page itself was not opened.")
    return _result("pending", None, "This certificate site is not on the trusted list, so it needs review.")


def trusted_domain(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    for entry in TRUSTED_CERTIFICATE_DOMAINS:
        domain, _, path = entry.partition("/")
        if (host == domain or host.endswith("." + domain)) and (not path or parsed.path.lower().startswith("/" + path)):
            return entry
    return None


def _github_get(path):
    """GET https://api.github.com{path}. Returns JSON, None for 404, raises GitHubUnavailable otherwise."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.get(f"https://api.github.com{path}", headers=headers, timeout=GITHUB_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise GitHubUnavailable(type(exc).__name__) from exc
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise GitHubUnavailable(f"HTTP {response.status_code}")
    return response.json()


def _rule(skill_name):
    return SKILL_RULES.get(skill_name, {"languages": [skill_name], "keywords": [skill_name.lower()]})


def skill_matches(skill_name, languages, text):
    """Returns a short reason when the repository shows the skill, otherwise None."""
    rule = _rule(skill_name)
    if rule.get("any"):
        return "any non-empty repository counts for this skill"
    repo_languages = {name.lower(): name for name in languages}
    language = next((repo_languages[l.lower()] for l in rule.get("languages", []) if l.lower() in repo_languages), None)
    keyword = next((k for k in rule.get("keywords", []) if re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", text)), None)
    if rule.get("all"):
        return f"language {language} and '{keyword}'" if language and keyword else None
    if language:
        return f"language {language}"
    return f"'{keyword}' in the repository details" if keyword else None


def check_github(url, skill_name):
    owner, repo = GITHUB_REPO_URL.match(url).groups()
    try:
        info = _github_get(f"/repos/{owner}/{repo}")
        if info is None:
            return _result("rejected", None, "The repository was not found or is not public.")
        languages = _github_get(f"/repos/{owner}/{repo}/languages") or {}
    except GitHubUnavailable as exc:
        return _result("pending", None, f"GitHub could not be checked right now ({exc}). The proof is kept for review.")
    if not info.get("size") and not languages:
        return _result("rejected", None, "The repository is empty.")
    text = " ".join([info.get("name") or "", info.get("description") or "", " ".join(info.get("topics") or [])]).lower()
    reason = skill_matches(skill_name, languages, text)
    if not reason:
        shown = ", ".join(list(languages)[:4]) or "no languages detected"
        return _result("rejected", None, f"The repository does not show {skill_name} ({shown}).")
    return _result("provisional", PROVISIONAL_LEVEL_LINK, f"GitHub repository {owner}/{repo} matches {skill_name}: {reason}.")
