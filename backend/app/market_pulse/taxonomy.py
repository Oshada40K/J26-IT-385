"""Maps raw job listings onto tracked careers and technical skills.

Careers are matched on the job title only (first rule that matches wins, most specific first).
Titles are English or German because Arbeitnow is a German-language board. Listings that match no
rule stay unclassified: they count towards market totals but not towards any career.
"""
import html
import re

# Titles that contain "developer"/"entwickler" but are not technology roles.
_NOT_TECH = re.compile(
    r"business develop|sales develop|talent develop|people develop|leadership develop|corporate develop"
    r"|organi[sz]ation\w* develop|real estate|property develop|learning (and|&) develop|curriculum|fundrais"
    r"|personalentwickl|gesch[aä]ftsentwickl|produktentwickl|projektentwickl|immobilien|organisationsentwickl"
    r"|gesch[aä]ftsfeldentwickl|standortentwickl|vertrieb|au[sß]endienst", re.I)

_CAREER_RULES = [
    ("Machine Learning / AI Engineer",
     r"machine learning|\bml[- ]?(engineer|ops|scientist|developer)|mlops|deep learning|computer vision|\bnlp\b|\bllm"
     r"|\b(gen)?ai[- ](engineer|developer|scientist|researcher|architect|platform|specialist|entwickler)"
     r"|\bki[- ](entwickler|engineer|ingenieur|spezialist)|artificial intelligence (engineer|developer)"
     r"|prompt engineer|applied scientist"),
    ("Data Scientist", r"data scien|datenwissenschaft"),
    ("Data Engineer",
     r"data engineer|dateningenieur|big data|\betl\b|analytics engineer|data platform|data ?warehouse|\bdwh\b"
     r"|databricks|snowflake"),
    ("Data Analyst",
     r"data analy|datenanaly|business intelligence|\bbi[- ](analyst|developer|engineer|entwickler|consultant|specialist)"
     r"|reporting analyst|power ?bi|analytics (analyst|specialist|manager|consultant)|product analyst|data ?analist"),
    ("Database Administrator", r"database (administrator|engineer|developer|specialist)|\bdba\b|datenbank|sql[- ](developer|entwickler)"),
    ("Cybersecurity Specialist",
     r"cyber|information security|it[- ]security|it[- ]sicherheit|informationssicherheit|penetration|pentest|infosec"
     r"|\bsoc\b|\bgrc\b|appsec|devsecops"
     r"|security (engineer|analyst|architect|consultant|specialist|operations|researcher|manager|lead)"),
    ("DevOps / Site Reliability Engineer",
     r"dev[- ]?ops|site reliability|\bsre\b|platform engineer|infrastructure engineer|kubernetes|release engineer|build engineer"),
    ("Cloud Engineer",
     r"cloud[- ](engineer|architect|developer|consultant|administrator|specialist|ingenieur|entwickler|operations|solution)"
     r"|\b(aws|azure|gcp)[- ](engineer|architect|developer|consultant|administrator|specialist|cloud|devops|entwickler)"),
    ("Solutions / Software Architect",
     r"(software|solutions?|enterprise|systems?|it|technical|data|security)[- ]?archite[ck]t|softwarearchitekt"
     r"|l[oö]sungsarchitekt"),
    ("QA / Test Engineer",
     r"\bqa[- ]?(engineer|analyst|tester|automation|lead|manager|specialist)|\bsdet\b|software ?test"
     r"|test[- ]?(automation|analyst|ingenieur)|testautomat|software quality"),
    ("Mobile Developer", r"android|\bios\b|mobile[- ](developer|engineer|entwickler|app)|flutter|react native|kotlin|swift (developer|engineer)"),
    ("Embedded Systems Engineer", r"embedded|firmware|\bfpga\b|sps[- ]?(programm|entwickl)|\bplc\b"),
    ("Game Developer", r"game[- ](developer|designer|programmer|engineer)|gameplay|\bunity\b|unreal engine"),
    ("Full Stack Developer", r"full[- ]?stack"),
    ("Frontend Developer",
     r"front[- ]?end|\breact|angular|vue(\.?js)?\b|ui[- ](developer|engineer|entwickler)"
     r"|web ?(developer|entwickler|engineer)|webentwickl|wordpress|shopify"),
    ("Backend Developer",
     r"back[- ]?end|\bjava\b|python[- ](developer|engineer|entwickler|programmer)|golang|\bgo (developer|engineer)"
     r"|node(\.?js)?\b|\.net\b|c#|\bphp\b|ruby|django|spring boot|api[- ](developer|engineer)|\brust\b|\bscala\b|c\+\+"),
    ("ERP / CRM Consultant", r"\bsap\b|\berp\b|\babap\b|dynamics ?365|salesforce|servicenow|\bodoo\b"),
    ("Engineering Manager",
     r"engineering manager|head of (engineering|software|it|development|technology)|\bcto\b|vp,? (of )?engineering"
     r"|tech(nical)? lead|team ?lead\w*.*(software|entwicklung|development|\bit\b)|it[- ]leit"),
    ("Software Engineer",
     r"software|softwareentwickl|\bdeveloper\b|programm(er|ierer)|anwendungsentwickl|applikations[- ]?entwickl"
     r"|\bsde\b|\bswe\b|\bentwickler\b|(product|staff|founding|forward deployed) engineer"),
    # After the developer rules, so "Software Engineer, UI" stays an engineer.
    ("UI/UX Designer", r"\bux\b|\bui\b|user experience|product design|interaction design|web ?design"),
    ("Product Manager", r"product (manager|owner|lead)|produktmanager|head of product|product management"),
    ("IT Project Manager",
     r"(\bit|software|technical|digital|agile)[- ]?(project|projekt|program|programme)[- ]?(manager|leiter|lead)"
     r"|scrum master|agile coach|delivery manager|projektmanager.*(\bit\b|software|digital)"),
    ("Business / Systems Analyst", r"business analyst|systems? analyst|requirements engineer|it[- ]analyst|anforderungsmanag"),
    ("Systems / Network Administrator",
     r"system ?administrator|sys ?admin|netzwerk|network[- ](engineer|administrator|architect|specialist|operations)"
     r"|it[- ]?administrator|(linux|windows|unix)[- ](administrator|engineer)|systems? engineer\b|systemingenieur"
     r"|it[- ]infrastruktur|it[- ]system|fachinformatiker.*systemintegration|systemintegrat"),
    ("IT Support Specialist",
     r"help ?desk|service ?desk|it[- ]support|technical support|support engineer|desktop support|it[- ]techniker"
     r"|it[- ]service|(1st|2nd|3rd|first|second|third)[- ]level[- ]support|application support|anwendungsbetreu"
     r"|it[- ](specialist|spezialist|mitarbeiter)|fachinformatiker"),
    ("IT Consultant",
     r"it[- ]?(consultant|berater|beratung|consulting)|technology consultant|technical consultant"
     r"|implementation consultant|digital\w* (consultant|berater)"),
    ("Technical Writer", r"technical writer|technische[rn]? redakteur|documentation (specialist|engineer|manager)"),
]
CAREER_RULES = [(name, re.compile(pattern, re.I)) for name, pattern in _CAREER_RULES]
CAREERS = [name for name, _ in CAREER_RULES]


def classify_career(title):
    """Returns the tracked career for a job title, or None when it is not a tracked role."""
    title = title or ""
    for name, pattern in CAREER_RULES:
        if pattern.search(title):
            if name in ("Software Engineer", "Frontend Developer") and _NOT_TECH.search(title):
                continue
            return name
    return None


# Skill name -> aliases matched case-insensitively as whole tokens.
_SKILL_ALIASES = {
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript"], "TypeScript": ["typescript"],
    "React": ["react.js", "reactjs"], "Angular": ["angular", "angularjs"], "Vue.js": ["vue.js", "vuejs"],
    "Node.js": ["node.js", "nodejs", "node js"], "SQL": ["sql"], "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"], "MongoDB": ["mongodb"], "NoSQL": ["nosql"], "Redis": ["redis"],
    "Machine Learning": ["machine learning", "maschinelles lernen"], "Deep Learning": ["deep learning"],
    "Generative AI / LLMs": ["generative ai", "genai", "gen ai", "llms", "large language model", "large language models"],
    "AWS": ["aws", "amazon web services"], "Azure": ["azure"], "Google Cloud": ["gcp", "google cloud"],
    "Docker": ["docker"], "Kubernetes": ["kubernetes", "k8s"], "Terraform": ["terraform"],
    "CI/CD": ["ci/cd", "ci cd", "continuous integration", "jenkins", "github actions", "gitlab ci"],
    "Git": ["git", "github", "gitlab"], "Linux": ["linux"],
    "C++": ["c++"], "C#": ["c#"], ".NET": [".net", "dotnet", "asp.net"], "PHP": ["php"], "Ruby": ["ruby", "ruby on rails"],
    "Kotlin": ["kotlin"], "Golang": ["golang"], "Kafka": ["kafka"], "TensorFlow": ["tensorflow"], "PyTorch": ["pytorch"],
    "Power BI": ["power bi", "powerbi"], "Salesforce": ["salesforce"],
    "Figma": ["figma"], "GraphQL": ["graphql"], "REST APIs": ["rest api", "rest apis", "restful"],
    "HTML/CSS": ["html", "css", "html5", "css3"], "Spring Boot": ["spring boot", "springboot"], "Django": ["django"],
    "Flutter": ["flutter"], "React Native": ["react native"], "Snowflake": ["snowflake"], "Databricks": ["databricks"],
    "Airflow": ["apache airflow"], "Pandas": ["pandas"], "Elasticsearch": ["elasticsearch"], "Ansible": ["ansible"],
}
# Names that are ordinary words in lower case (or in German/French), so they are matched case-sensitively.
_SKILL_EXACT = {
    "React": ["React"], "Vue.js": ["Vue"], "Tableau": ["Tableau"], "SAP": ["SAP"], "Airflow": ["Airflow"],
    "Generative AI / LLMs": ["LLM"],
    "Golang": [r"Go(?= (?:developer|engineer|programming|backend|services|microservices))"],
    "Rust": ["Rust"], "Swift": ["Swift", "SwiftUI"], "Scala": ["Scala"], "Excel": ["Excel"],
    "Apache Spark": ["Spark", "PySpark"], "R": [r"R(?=\s*(?:,|/|and|or)\s*(?:Python|SQL|SAS|Stata|MATLAB))", r"(?<=Python or )R", r"(?<=Python and )R", r"(?<=Python, )R", r"(?<=Python/)R"],
}
SKILLS = sorted({*_SKILL_ALIASES, *_SKILL_EXACT})

_BOUNDARY = r"(?<![A-Za-z0-9+#.]){}(?![A-Za-z0-9+#])"
_ALIAS_TO_SKILL = {alias: skill for skill, aliases in _SKILL_ALIASES.items() for alias in aliases}
_ALIAS_PATTERN = re.compile(
    _BOUNDARY.format("(" + "|".join(re.escape(a) for a in sorted(_ALIAS_TO_SKILL, key=len, reverse=True)) + ")"), re.I)
_EXACT_PATTERNS = [(skill, re.compile(_BOUNDARY.format("(?:" + "|".join(patterns) + ")")))
                   for skill, patterns in _SKILL_EXACT.items()]
_TAGS = re.compile(r"<[^>]+>")


def plain_text(value):
    """HTML job description -> plain text."""
    return html.unescape(_TAGS.sub(" ", value or ""))


def extract_skills(*texts):
    """Sorted tracked skills mentioned in any of the texts (title, tags, description)."""
    text = " \n ".join(t for t in texts if t)
    found = {_ALIAS_TO_SKILL[match.lower()] for match in _ALIAS_PATTERN.findall(text)}
    found.update(skill for skill, pattern in _EXACT_PATTERNS if pattern.search(text))
    return sorted(found)
