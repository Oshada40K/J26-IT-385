# Owner: Dewmi - Component 04.
"""Simple, safe checks for optional skill proof, run right after upload (and again on "Check again").

Component 01 is the main verifier. Until it is connected, these checks can only give a capped
PROVISIONAL level:
- github            GitHub REST API: the repository must exist, not be empty, be owned or contributed to
                    by the student, and show signs of the skill (languages, topics, README, file names,
                    dependency files).
- certificate_link  the URL is never fetched; only its domain is compared with a trusted list.
- certificate_file  cannot be checked automatically, so it stays pending review but counts as level 2.

Every check returns {status, provisional_level, status_reason, check_details}; check_details is a list of
{check, result: passed | failed | not_checked, detail} written in simple English for the student.
"""
import base64
import fnmatch
import os
import re
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx

from .errors import EvidenceError

PROVISIONAL_LEVEL_LINK = 3          # out of 5: trusted certificate link or matching GitHub repository
PROVISIONAL_LEVEL_FILE = 2          # out of 5: uploaded certificate file, pending review
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_DESCRIPTION = 500
PROOF_TYPES = ("github", "certificate_link", "certificate_file")
GITHUB_TIMEOUT_SECONDS = 5
GITHUB_HOSTS = ("github.com", "www.github.com")
GITHUB_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
GITHUB_REPO = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
MAX_TREE_PATHS = 20000              # file names looked at in one repository
MAX_TEXT_CHARS = 200_000            # README / dependency file text looked at
MAX_MANIFESTS = 3                   # dependency files read per check (each is one API call)
TRUSTED_CERTIFICATE_DOMAINS = (
    "credly.com", "coursera.org", "udemy.com", "linkedin.com/learning", "aws.amazon.com", "learn.microsoft.com",
    "cloud.google.com", "freecodecamp.org", "hackerrank.com", "cisco.com", "oracle.com",
)
# File signature -> allowed extensions (checked on content, not only on the file name).
FILE_SIGNATURES = {b"%PDF": (".pdf",), b"\x89PNG\r\n\x1a\n": (".png",), b"\xff\xd8\xff": (".jpg", ".jpeg")}

# Reasons shown to the student (kept short and stable).
REASON_UNREACHABLE = "Could not reach GitHub, try again."
REASON_NOT_OWNER = "Repository is not owned by / contributed to by this student."
REASON_NO_USERNAME = ("We could not check that this repository is yours because Component 01 has no GitHub "
                      "username for you. Add your GitHub username when you upload your CV in Component 01, "
                      "then press Check again.")

# Dependency files whose text is searched for "packages" (only when the skill has packages).
MANIFESTS = ("requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "environment.yml", "package.json",
             "pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "Gemfile", "go.mod")

# Signs of a skill in a repository. "languages": GitHub languages; "keywords": words in the name, description,
# topics or README; "files": file names (fnmatch on the name) or folder names ending in "/"; "packages":
# names inside dependency files. "any": every non-empty repository counts; "all": a language AND one other
# sign must match. Skills not listed use their own name (see _rule).
SKILL_RULES = {
    "Git": {"any": True},
    "Programming Fundamentals": {"any": True},
    "Java": {"languages": ["Java"]},
    "Spring Boot": {"languages": ["Java", "Kotlin"], "keywords": ["spring", "spring boot"],
                    "packages": ["spring-boot", "spring-boot-starter"], "all": True},
    "Python": {"languages": ["Python", "Jupyter Notebook"]},
    "JavaScript": {"languages": ["JavaScript", "TypeScript"]},
    "TypeScript": {"languages": ["TypeScript"], "files": ["tsconfig.json"]},
    "HTML and CSS": {"languages": ["HTML", "CSS", "SCSS"]},
    "React": {"languages": ["JavaScript", "TypeScript"], "keywords": ["react", "next.js", "nextjs"],
              "packages": ["react", "next", "react-native"], "all": True},
    "Angular": {"languages": ["TypeScript"], "keywords": ["angular"], "files": ["angular.json"],
                "packages": ["@angular/core"], "all": True},
    "Node.js": {"languages": ["JavaScript", "TypeScript"], "keywords": ["node", "nodejs", "express", "nestjs"],
                "files": ["package.json"], "packages": ["express", "@nestjs/core", "koa", "fastify"], "all": True},
    "Django": {"languages": ["Python"], "keywords": ["django"], "files": ["manage.py"], "packages": ["django"],
               "all": True},
    ".NET": {"languages": ["C#", "F#"], "keywords": [".net", "dotnet", "asp.net"], "files": ["*.csproj", "*.sln"]},
    "C#": {"languages": ["C#"]},
    "C++": {"languages": ["C++"]},
    "C": {"languages": ["C"]},
    "Embedded C": {"languages": ["C"], "keywords": ["embedded", "arduino", "stm32", "firmware"],
                   "files": ["*.ino", "platformio.ini"], "all": True},
    "PHP": {"languages": ["PHP"]},
    "Kotlin": {"languages": ["Kotlin"]},
    "R": {"languages": ["R"]},
    "Solidity": {"languages": ["Solidity"], "files": ["*.sol", "hardhat.config.*", "truffle-config.js"]},
    "Verilog and FPGA": {"languages": ["Verilog", "SystemVerilog", "VHDL"]},
    "Object-Oriented Programming": {"languages": ["Java", "C#", "C++", "Python", "Kotlin", "TypeScript"]},
    "Data Structures and Algorithms": {"keywords": ["algorithm", "algorithms", "data structure", "data structures",
                                                    "leetcode", "dsa"]},
    "SQL": {"languages": ["TSQL", "PLpgSQL", "PLSQL"], "keywords": ["sql", "mysql", "postgres", "database"],
            "files": ["*.sql"]},
    "PostgreSQL": {"languages": ["PLpgSQL"], "keywords": ["postgres", "postgresql"],
                   "packages": ["psycopg2", "psycopg2-binary", "psycopg", "pg", "asyncpg"]},
    "MongoDB": {"keywords": ["mongo", "mongodb"], "packages": ["mongoose", "mongodb", "pymongo", "motor"]},
    "Bash Scripting": {"languages": ["Shell"], "keywords": ["bash", "shell"], "files": ["*.sh"]},
    "Linux": {"languages": ["Shell"], "keywords": ["linux"]},
    "Docker": {"languages": ["Dockerfile"], "keywords": ["docker"],
               "files": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml", ".dockerignore"]},
    "Kubernetes": {"keywords": ["kubernetes", "k8s", "helm"],
                   "files": ["Chart.yaml", "kustomization.yaml", "skaffold.yaml", "k8s/", "helm/"]},
    "Terraform": {"languages": ["HCL"], "keywords": ["terraform"], "files": ["*.tf", ".terraform.lock.hcl"]},
    "CI/CD": {"keywords": ["ci/cd", "github actions", "pipeline", "jenkins"],
              "files": [".github/workflows/", "Jenkinsfile", ".gitlab-ci.yml", ".circleci/", "azure-pipelines.yml",
                        "buildspec.yml", ".travis.yml"]},
    "AWS": {"keywords": ["aws", "amazon web services", "cloudformation", "dynamodb", "ec2", "amplify"],
            "files": ["serverless.yml", "serverless.yaml", "samconfig.toml", "cdk.json",
                      "buildspec.yml", "appspec.yml", "*cloudformation*", ".aws/", "amplify/", "cloudformation/",
                      ".ebextensions/"],
            "packages": ["aws-sdk", "@aws-sdk/", "boto3", "botocore", "aws-cdk", "aws-cdk-lib", "aws-amplify",
                         "@aws-amplify/", "awscli", "aws-lambda-powertools", "serverless", "com.amazonaws"]},
    "Microsoft Azure": {"keywords": ["azure"], "files": ["azure-pipelines.yml", "host.json", ".azure/"],
                        "packages": ["@azure/", "azure-"]},
    "Pandas": {"languages": ["Python", "Jupyter Notebook"], "keywords": ["pandas"], "packages": ["pandas"],
               "all": True},
    "NumPy": {"languages": ["Python", "Jupyter Notebook"], "keywords": ["numpy"], "packages": ["numpy"], "all": True},
    "Machine Learning": {"languages": ["Python", "Jupyter Notebook", "R"],
                         "keywords": ["machine learning", "ml", "scikit", "sklearn", "model"],
                         "packages": ["scikit-learn", "sklearn", "xgboost", "lightgbm", "tensorflow", "torch"],
                         "all": True},
    "Deep Learning": {"keywords": ["deep learning", "pytorch", "tensorflow", "keras", "neural"],
                      "packages": ["torch", "tensorflow", "keras", "pytorch-lightning"]},
    "Natural Language Processing": {"keywords": ["nlp", "natural language", "text classification", "transformers"],
                                    "packages": ["nltk", "spacy", "transformers", "gensim"]},
    "Generative AI and LLMs": {"keywords": ["llm", "gpt", "langchain", "generative", "rag"],
                               "packages": ["openai", "anthropic", "langchain", "llama-index", "transformers"]},
    "Test Automation": {"keywords": ["test", "automation", "pytest", "junit", "cypress", "playwright"],
                        "files": ["pytest.ini", "jest.config.*", "cypress.config.*", "playwright.config.*", "cypress/"],
                        "packages": ["pytest", "jest", "junit", "cypress", "@playwright/test", "playwright"]},
    "Selenium": {"keywords": ["selenium"], "packages": ["selenium", "selenium-webdriver"]},
    "Unity": {"languages": ["C#", "ShaderLab"], "keywords": ["unity"], "files": ["ProjectSettings/", "*.unity"]},
    "REST API Design": {"keywords": ["api", "rest", "openapi", "swagger"],
                        "files": ["openapi.yaml", "openapi.yml", "openapi.json", "swagger.json", "swagger.yaml"]},
}


class GitHubUnavailable(RuntimeError):
    pass


def _step(check, result, detail):
    return {"check": check, "result": result, "detail": detail}


def _result(status, level, reason, details):
    return {"status": status, "provisional_level": level, "status_reason": reason, "check_details": details}


# ------------------------------------------------------------------ validation (400 errors)
def normalize_github_url(url):
    """https://github.com/<owner>/<repo> from a pasted repository link, or None when it is not one.
    Removes ".git", a trailing "/", "/tree/...", "/blob/...", "?query" and "#fragment"."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in GITHUB_HOSTS or parsed.port \
            or parsed.username or parsed.password:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or (len(parts) > 2 and parts[2] not in ("tree", "blob")):
        return None
    owner, repo = parts[0], parts[1]
    repo = repo[:-4] if repo.lower().endswith(".git") else repo
    if not GITHUB_OWNER.match(owner) or not GITHUB_REPO.match(repo) or repo in (".", ".."):
        return None
    return f"https://github.com/{owner}/{repo}"


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
    if proof_type == "github":
        url = normalize_github_url(url)
        if not url:
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
def check(proof_type, url, skill_name, github_usernames=(), file_name=None, file_size=None):
    """github_usernames: the student's GitHub usernames from Component 01 (may be empty)."""
    if proof_type == "github":
        return check_github(url, skill_name, github_usernames)
    if proof_type == "certificate_link":
        return check_certificate_link(url)
    return check_certificate_file(file_name, file_size)


def check_certificate_file(file_name=None, file_size=None):
    size = f", {max(1, round(file_size / 1024))} KB" if file_size else ""
    kind = (Path(file_name or "").suffix.lstrip(".") or "file").upper()
    return _result("pending", PROVISIONAL_LEVEL_FILE,
                   "Certificate file received. Files cannot be checked automatically, so it waits for a reviewer. "
                   f"Until then it counts as level {PROVISIONAL_LEVEL_FILE}/5.",
                   [_step("File type and size", "passed", f"{kind}{size}: an accepted file type under 5 MB."),
                    _step("Reviewer check", "not_checked", "A reviewer has not looked at this file yet.")])


def check_certificate_link(url):
    """Never fetches the link (security); only compares the domain with the trusted list."""
    steps = [_step("Link format", "passed", "The link is a full https:// address.")]
    domain = trusted_domain(url)
    if domain:
        steps.append(_step("Trusted certificate site", "passed",
                           f"{domain} is on the trusted list. The page itself was not opened."))
        return _result("provisional", PROVISIONAL_LEVEL_LINK,
                       f"Certificate link from a trusted provider ({domain}). Counts as level "
                       f"{PROVISIONAL_LEVEL_LINK}/5 until Component 01 confirms it.", steps)
    steps.append(_step("Trusted certificate site", "failed",
                       f"{urlparse(url).hostname} is not on the trusted list of certificate sites."))
    return _result("pending", None, "This certificate site is not on the trusted list, so a reviewer needs to check it.",
                   steps)


def trusted_domain(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    for entry in TRUSTED_CERTIFICATE_DOMAINS:
        domain, _, path = entry.partition("/")
        if (host == domain or host.endswith("." + domain)) and (not path or parsed.path.lower().startswith("/" + path)):
            return entry
    return None


def _github_get(path):
    """GET https://api.github.com{path}. Returns JSON; None for 404 (not found), 409 (empty repository) and
    204 (no content). Raises GitHubUnavailable for network errors, rate limits and other errors."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        # follow_redirects: renamed or transferred repositories answer with 301.
        response = httpx.get(f"https://api.github.com{path}", headers=headers, timeout=GITHUB_TIMEOUT_SECONDS,
                             follow_redirects=True)
    except httpx.HTTPError as exc:
        raise GitHubUnavailable(f"network error ({type(exc).__name__})") from exc
    if response.status_code in (204, 404, 409):
        return None
    if response.status_code == 429 or (response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"):
        raise GitHubUnavailable("GitHub rate limit reached")
    if response.status_code != 200:
        raise GitHubUnavailable(f"GitHub answered HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise GitHubUnavailable("GitHub sent an unreadable answer") from exc


def _decoded(content_json):
    """Text of a /readme or /contents/<path> answer (base64), or ''."""
    if not isinstance(content_json, dict) or content_json.get("encoding") != "base64":
        return ""
    try:
        return base64.b64decode(content_json.get("content") or "").decode("utf-8", "replace")[:MAX_TEXT_CHARS]
    except ValueError:
        return ""


def _rule(skill_name):
    return SKILL_RULES.get(skill_name, {"languages": [skill_name], "keywords": [skill_name.lower()]})


def _word(term, text):
    """term appears in text as a whole word (case-insensitive)."""
    return re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", text) is not None


def _package(name, text):
    """A dependency name inside a dependency file ("@aws-sdk/" style prefixes match any package under them)."""
    tail = "" if name.endswith(("/", "-", ".")) else r"(?![A-Za-z0-9_-])"
    return re.search(rf"(?<![A-Za-z0-9_-]){re.escape(name.lower())}{tail}", text) is not None


def _file_match(pattern, paths):
    """First repository path matching a file-name pattern, or a folder pattern ending in "/"."""
    pattern = pattern.lower()
    for path in paths:
        lower = path.lower()
        if pattern.endswith("/"):
            if ("/" + lower + "/").find("/" + pattern) >= 0:
                return path
        elif fnmatch.fnmatchcase(lower.rsplit("/", 1)[-1], pattern):
            return path
    return None


class _SkillScan:
    """Collects signs of one skill in a repository, step by step, so later (costly) steps run only when needed."""

    def __init__(self, skill_name):
        self.rule = _rule(skill_name)
        self.language = None
        self.signs = []                        # other signs: keywords, files, packages
        self.looked_at = []

    @property
    def found(self):
        if self.rule.get("all"):
            return bool(self.language and self.signs)
        return bool(self.language or self.signs)

    def languages(self, languages):
        self.looked_at.append("languages")
        repo_languages = {name.lower(): name for name in languages}
        self.language = next((repo_languages[l.lower()] for l in self.rule.get("languages", [])
                              if l.lower() in repo_languages), None)

    def text(self, where, text):
        self.looked_at.append(where)
        text = text.lower()
        keyword = next((k for k in self.rule.get("keywords", []) if _word(k, text)), None)
        if keyword:
            self.signs.append(f"'{keyword}' in the {where}")

    def files(self, paths):
        self.looked_at.append(f"{len(paths)} file names")
        for pattern in self.rule.get("files", []):
            path = _file_match(pattern, paths)
            if path:
                self.signs.append(f"file {path}")
                return

    def manifest(self, path, text):
        text = text.lower()
        package = next((p for p in self.rule.get("packages", []) if _package(p, text)), None)
        if package:
            self.signs.append(f"{package.rstrip('/')} in {path}")

    def summary(self):
        found = ([f"language {self.language}"] if self.language else []) + self.signs
        return "; ".join(found)


def check_github(url, skill_name, github_usernames=()):
    """Checks a (normalised) GitHub repository link. Never raises: GitHub problems keep the proof pending."""
    original = url
    url = normalize_github_url(url) or url
    owner, repo = url.removeprefix("https://github.com/").split("/")[:2]
    steps = [_step("Link format", "passed", f"Repository link: {url}" + ("" if url == original else
                                                                          f" (cleaned from {original})"))]
    usernames = {u.lower() for u in github_usernames if u}

    def unreachable(check, exc):
        steps.append(_step(check, "not_checked", f"{exc}. Nothing was decided."))
        return _result("pending", None, REASON_UNREACHABLE, steps)

    # 1. The repository exists and is not empty.
    try:
        info = _github_get(f"/repos/{owner}/{repo}")
    except GitHubUnavailable as exc:
        return unreachable("Repository found", exc)
    if not isinstance(info, dict):
        steps.append(_step("Repository found", "failed", "GitHub has no public repository at this link."))
        return _result("rejected", None, "The repository was not found or is not public.", steps)
    full_name = info.get("full_name") or f"{owner}/{repo}"
    real_owner = (info.get("owner") or {}).get("login") or owner
    steps.append(_step("Repository found", "passed", f"{full_name} is a public repository."))
    try:
        languages = _github_get(f"/repos/{full_name}/languages") or {}
    except GitHubUnavailable as exc:
        return unreachable("Repository not empty", exc)
    if not info.get("size") and not languages:
        steps.append(_step("Repository not empty", "failed", "The repository has no code."))
        return _result("rejected", None, "The repository is empty.", steps)
    steps.append(_step("Repository not empty", "passed",
                       f"Languages: {', '.join(list(languages)[:5])}." if languages else "The repository has files."))

    # 2. Ownership: the owner is the student, or the student is a contributor (a fork alone is not enough).
    owner_check = "Owned by or contributed to by you"
    ownership = None                                     # True / False / None (no username to compare)
    if usernames:
        if real_owner.lower() in usernames and not info.get("fork"):
            ownership = True
            steps.append(_step(owner_check, "passed", f"The owner '{real_owner}' is your GitHub username."))
        else:
            try:
                contributors = _github_get(f"/repos/{full_name}/contributors?per_page=100") or []
            except GitHubUnavailable as exc:
                return unreachable(owner_check, exc)
            logins = {(c.get("login") or "").lower() for c in contributors if isinstance(c, dict)}
            match = next((u for u in sorted(usernames) if u in logins), None)
            ownership = bool(match)
            if match:
                steps.append(_step(owner_check, "passed", f"You ('{match}') are in the contributors list."))
            else:
                fork = " It is a fork, and you have no commits in it." if info.get("fork") else ""
                steps.append(_step(owner_check, "failed",
                                   f"The owner is '{real_owner}', and your GitHub username "
                                   f"({', '.join(sorted(usernames))}) is not in the contributors list.{fork}"))
    else:
        steps.append(_step(owner_check, "not_checked", "Component 01 has no GitHub username for you to compare with."))
    if ownership is False:
        steps.append(_step(f"Shows {skill_name}", "not_checked", "Skipped because the repository is not yours."))
        return _result("rejected", None, REASON_NOT_OWNER, steps)

    # 3. Skill usage: languages, topics/description, README, file names, dependency files.
    skill_check = f"Shows {skill_name}"
    scan = _SkillScan(skill_name)
    if scan.rule.get("any"):
        steps.append(_step(skill_check, "passed", f"Any non-empty repository counts for {skill_name}."))
    else:
        scan.languages(languages)
        scan.text("name, description and topics", " ".join(
            [info.get("name") or "", info.get("description") or "", " ".join(info.get("topics") or [])]))
        try:
            if not scan.found:
                scan.text("README", _decoded(_github_get(f"/repos/{full_name}/readme")))
            if not scan.found and (scan.rule.get("files") or scan.rule.get("packages")):
                branch = quote(info.get("default_branch") or "HEAD", safe="")
                tree = _github_get(f"/repos/{full_name}/git/trees/{branch}?recursive=1") or {}
                paths = [t["path"] for t in tree.get("tree", []) if isinstance(t, dict) and t.get("type") == "blob"
                         and isinstance(t.get("path"), str)][:MAX_TREE_PATHS]
                scan.files(paths)
                if not scan.found and scan.rule.get("packages"):
                    manifests = sorted((p for p in paths if p.rsplit("/", 1)[-1] in MANIFESTS),
                                       key=lambda p: (p.count("/"), p))[:MAX_MANIFESTS]
                    for path in manifests:
                        scan.manifest(path, _decoded(_github_get(f"/repos/{full_name}/contents/{quote(path)}")))
                        if scan.found:
                            break
                    if manifests:
                        scan.looked_at.append("dependency files (" + ", ".join(manifests) + ")")
        except GitHubUnavailable as exc:
            return unreachable(skill_check, exc)
        if not scan.found:
            needs = " (it needs a matching language and one other sign)" if scan.rule.get("all") else ""
            partial = f" Found only: {scan.summary()}." if scan.summary() else ""
            steps.append(_step(skill_check, "failed", f"Looked at {', '.join(scan.looked_at)}; no signs of "
                                                      f"{skill_name} were found{needs}.{partial}"))
            return _result("rejected", None, f"No signs of {skill_name} were found in this repository.", steps)
        steps.append(_step(skill_check, "passed", f"Found: {scan.summary()}."))

    if ownership is None:
        return _result("pending", None, REASON_NO_USERNAME, steps)
    return _result("provisional", PROVISIONAL_LEVEL_LINK,
                   f"GitHub repository {full_name} is yours and shows {skill_name}. Counts as level "
                   f"{PROVISIONAL_LEVEL_LINK}/5 until Component 01 confirms it.", steps)
