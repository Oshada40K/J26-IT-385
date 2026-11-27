"""Domain-independent dynamic NLP candidate extraction from CV sections."""
import re

SECTION_LABEL_PREFIX = re.compile(
    r'^(?:technical\s+skills?|skills?|core\s+competencies|competencies|tools?(?:\s*&\s*|\s+and\s+platforms?)?|'
    r'technologies|languages?|programming\s+languages?|frameworks?|databases?|certifications?|'
    r'clinical\s+skills?|financial\s+skills?|marketing\s+skills?|design\s+tools?|software|frontend|backend(?:\s*&\s*data)?|'
    r'testing(?:\s*/\s*qa)?|other)\s*[:\-–—]\s*',
    re.I,
)

# Phrases that are generic CV prose, headings, or non-skill artifacts rather than skills.
STOP_CANDIDATES = {
    'skills', 'technical skills', 'summary', 'experience', 'projects', 'education', 'certifications',
    'references', 'curriculum vitae', 'resume', 'profile', 'objective', 'about me', 'work experience',
    'fictional', 'sample', 'example', 'hybrid', 'remote', 'onsite', 'full time', 'part time',
    'present', 'current', 'team player', 'good communication', 'hard worker', 'fast learner',
    'self motivated', 'detail oriented', 'bachelor', 'master', 'phd', 'bsc', 'msc', 'mba', 'ba', 'bs',
    'university', 'institute', 'college', 'school', 'academy', 'company', 'studio', 'inc', 'ltd', 'llc',
    'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec',
    'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
    'year', 'years', 'month', 'months', 'day', 'days', 'role', 'responsibilities', 'achievements',
    'key features', 'user registration', 'user experience', 'client', 'clients', 'customer', 'customers',
    'team', 'teams', 'features', 'feature', 'system', 'systems', 'application', 'applications',
    'project', 'projects', 'work', 'tasks', 'task', 'results', 'issues', 'fixes', 'views', 'cards',
    'forms', 'tables', 'workflows', 'workflow', 'solutions', 'solution', 'services', 'service',
    'data', 'reports', 'report', 'meetings', 'daily', 'challenges', 'conferences', 'experience',
    'developer', 'developers', 'engineer', 'engineers', 'designer', 'designers', 'user', 'users',
    'stakeholder', 'stakeholders', 'colleague', 'colleagues', 'manager', 'managers', 'patients',
    'students', 'employees', 'staff', 'members', 'github', 'linkedin',
}

GENERIC_START_WORDS = {'a', 'an', 'the', 'my', 'our', 'their', 'this', 'that', 'these', 'those', 'some', 'any', 'all', 'various', 'multiple', 'several', 'new', 'existing', 'key', 'good', 'strong', 'excellent', 'basic', 'advanced'}

# Action-object and tool-preposition patterns that work across IT, Finance, Healthcare, Education, Engineering, Marketing, Design.
TOOL_PREP_PATTERN = re.compile(
    r'(?:\b(?:using|via|utilizing|leveraging|proficient in|certified in|experienced in|skilled in|trained in|expertise in)|'
    r'\b(?:built|developed|implemented|designed|created|tested|analyzed|analysed|audited|configured|monitored|automated|managed|integrated|trained|prototyped|prepared)\s+with)\s+'
    r'([A-Za-z0-9][A-Za-z0-9.+#/&\- ]{1,42}?)(?=\s*(?:,|;|\.|for\b|to\b|and\b|or\b|in\b|on\b|at\b|$))',
    re.I,
)

# Capitalized multi-word phrases or domain certifications/acronyms (e.g., "Financial Modeling", "IFRS 17", "Patient Triage", "Six Sigma").
PROPER_PHRASE_PATTERN = re.compile(
    r'\b([A-Z][A-Za-z0-9.+#/&\-]*(?:\s+(?:of|and|for|in)?\s*[A-Z0-9][A-Za-z0-9.+#/&\-]*){1,3})\b'
)


def _clean_candidate(raw: str) -> str:
    text = re.sub(r'\s+', ' ', (raw or '').strip(' \t\r\n•●▪-–—.,;:()[]{}"\'')).strip()
    # Strip trailing parenthetical qualifiers like "Epic (EHR)" -> keep main if clean, or split.
    text = re.sub(r'\([^)]{0,40}\)$', '', text).strip()
    return text


def is_valid_skill_candidate(phrase: str) -> bool:
    if not phrase or len(phrase) < 2 or len(phrase) > 50:
        return False
    if re.search(r'https?://|@|\d{4}\s*[-–]\s*(?:\d{4}|present)', phrase, re.I):
        return False
    if re.fullmatch(r'[\d\W]+', phrase):
        return False
    words = phrase.split()
    if len(words) > 4:
        return False
    low = phrase.casefold()
    if low in STOP_CANDIDATES:
        return False
    if words[0].casefold() in GENERIC_START_WORDS:
        return False
    # Single lowercase generic words are usually prose nouns, not standalone skills.
    if len(words) == 1 and phrase.islower() and len(phrase) < 6:
        return False
    if any(w in {'fictional', 'sample', 'employer', 'institute', 'technology'} for w in low.split()):
        return False
    return True


def extract_nlp_candidates(units: list[dict], positive_context_fn) -> list[dict]:
    """Extract dynamic candidate skill phrases from CV evidence units across any career field."""
    candidates = []
    seen = set()

    def add_candidate(raw_phrase: str, unit: dict, match_start: int, origin: str):
        cleaned = _clean_candidate(raw_phrase)
        if not is_valid_skill_candidate(cleaned):
            return
        if not positive_context_fn(unit['text'], max(0, match_start)):
            return
        key = (cleaned.casefold(), unit['section'], unit['start'])
        if key in seen:
            return
        seen.add(key)
        candidates.append({
            'phrase': cleaned,
            'section': unit['section'],
            'text': unit['text'],
            'unit_start': unit['start'],
            'match_start': match_start,
            'origin': origin,
        })

    for unit in units:
        section = unit.get('section', 'other')
        text = unit.get('text', '')
        if not text:
            continue

        # 1. Structured lists in skills or certifications sections (or inline "Tools: A, B, C").
        if section in {'skills', 'certifications'} or SECTION_LABEL_PREFIX.match(text):
            stripped = SECTION_LABEL_PREFIX.sub('', text)
            for part in re.split(r'\s*[,|;•●▪]\s*|\s+/\s+', stripped):
                # Also handle "and" inside short lists, e.g. "GAAP and IFRS"
                subparts = re.split(r'\s+\band\b\s+', part) if len(part.split()) <= 5 else [part]
                for sub in subparts:
                    pos = text.find(sub.strip())
                    add_candidate(sub, unit, max(0, pos), 'structured_list')
            continue

        # 2. Experience & Projects: extract tool/method prepositional phrases and proper domain concepts.
        if section in {'projects', 'experience', 'education'}:
            for m in TOOL_PREP_PATTERN.finditer(text):
                raw_group = m.group(1)
                for sub in re.split(r'\s*[,/]\s*|\s+\band\b\s+', raw_group):
                    add_candidate(sub, unit, m.start(1), 'nlp_preposition')

            for m in PROPER_PHRASE_PATTERN.finditer(text):
                phrase = m.group(1)
                # Avoid matching sentence-initial 2-word verb+noun clauses like "Built Reusable" or company names.
                if m.start() == 0:
                    continue
                if re.search(r'\b(?:Inc|Ltd|LLC|Corp|Studio|University|Institute|College|School|Hospital|Clinic)\b', phrase):
                    continue
                add_candidate(phrase, unit, m.start(1), 'nlp_noun_phrase')

    return candidates
