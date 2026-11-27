"""Dynamic 7-category skill classifier across all professional domains."""
import re

CATEGORIES = (
    'Technical skills',
    'Programming languages',
    'Frameworks and libraries',
    'Tools and platforms',
    'Databases',
    'Domain-specific skills',
    'Soft skills',
)

PROGRAMMING_LANGUAGES = {
    'python', 'javascript', 'typescript', 'java', 'c', 'c++', 'c#', 'go', 'r', 'php', 'ruby',
    'swift', 'kotlin', 'rust', 'dart', 'scala', 'perl', 'bash', 'sql', 'pl/sql', 't-sql',
    'matlab', 'julia', 'sas', 'vba', 'powershell', 'objective-c', 'groovy', 'haskell', 'elixir',
}

FRAMEWORKS_AND_LIBRARIES = {
    'react', 'node.js', 'express.js', 'vue', 'angular', 'next.js', 'django', 'flask', 'fastapi',
    'spring boot', '.net', 'flutter', 'tensorflow', 'pytorch', 'keras', 'pandas', 'numpy',
    'scikit-learn', 'matplotlib', 'seaborn', 'scipy', 'langchain', 'hugging face', 'opencv',
    'jest', 'cypress', 'playwright', 'pytest', 'selenium', 'bootstrap', 'tailwind css', 'jquery',
    'laravel', 'ruby on rails', 'asp.net', 'react native', 'redux',
}

DATABASES = {
    'postgresql', 'mongodb', 'mysql', 'sqlite', 'redis', 'oracle database', 'microsoft sql server',
    'mariadb', 'cassandra', 'dynamodb', 'elasticsearch', 'snowflake', 'bigquery', 'firebase',
    'neo4j', 'microsoft access', 'couchdb', 'amazon rds', 'database tuning', 'database replication',
    'schema design', 'backup and recovery',
}

SOFT_KEYWORDS = re.compile(
    r'\b(?:communication|leadership|teamwork|collaboration|problem solving|critical thinking|'
    r'time management|active listening|negotiation|persuasion|mentoring|coaching|empathy|'
    r'adaptability|decision making|conflict resolution|stakeholder management|presentation skills|'
    r'reading comprehension|coordination|instructing|service orientation|monitoring|writing|speaking|'
    r'interpersonal|work ethic|attention to detail|emotional intelligence|creativity)\b',
    re.I,
)

FRAMEWORK_HINTS = re.compile(r'\b(?:framework|library|sdk|orm|toolkit)\b|\.(?:js|py)$', re.I)
DATABASE_HINTS = re.compile(r'\b(?:database|dbms|rdbms|sql|nosql|data warehouse|data lake)\b', re.I)
TOOL_HINTS = re.compile(
    r'\b(?:platform|software|tool|suite|system|ide|crm|erp|ehr|emr|cad|gis|siem|bi|cloud|'
    r'excel|tableau|power bi|looker|figma|adobe|sketch|jira|confluence|servicenow|salesforce|'
    r'quickbooks|sap|workday|hubspot|autocad|solidworks|revit|matlab|spss|stata|epic|cerner|'
    r'wireshark|nmap|burp suite|metasploit|docker|kubernetes|terraform|ansible|git|github|'
    r'gitlab|postman|vs code|aws|azure|google cloud|linux|windows server|active directory|moodle|canvas)\b',
    re.I,
)
TECH_HINTS = re.compile(
    r'\b(?:api|rest|graphql|ci/cd|devops|mlops|cloud|networking|tcp/ip|dns|dhcp|vpn|vlan|'
    r'cybersecurity|penetration testing|cryptography|machine learning|deep learning|'
    r'natural language processing|computer vision|data engineering|etl|testing|automation|'
    r'web development|system administration|virtualization|subnetting|routing|firewall)\b',
    re.I,
)


def classify_skill_category(name: str, description: str = '', o_net_categories: list[str] | None = None,
                            skill_type: str = 'skill') -> str:
    """Assign one of the 7 dynamic categories without restricting to IT."""
    lower = (name or '').strip().casefold()
    desc = (description or '').casefold()
    cats = ' '.join(o_net_categories or []).casefold()

    if skill_type == 'soft' or SOFT_KEYWORDS.search(lower):
        return 'Soft skills'
    if lower in PROGRAMMING_LANGUAGES:
        return 'Programming languages'
    if lower in DATABASES or DATABASE_HINTS.search(lower) or 'database' in cats:
        return 'Databases'
    if lower in FRAMEWORKS_AND_LIBRARIES or FRAMEWORK_HINTS.search(lower):
        return 'Frameworks and libraries'
    if TOOL_HINTS.search(lower) or any(tok in cats for tok in ('software', 'spreadsheet', 'crm', 'erp', 'cad', 'graphics', 'office', 'accounting software', 'medical software')):
        return 'Tools and platforms'
    if TECH_HINTS.search(lower) or TECH_HINTS.search(desc):
        return 'Technical skills'
    return 'Domain-specific skills'
