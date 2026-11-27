"""Bounded PDF/DOCX parsing; uploaded bytes are never saved to disk."""
import io
import re
import zipfile
from pathlib import Path
from ..config import MAX_FILE_BYTES, MAX_PAGES, MAX_TEXT_CHARS


class CVError(ValueError):
    pass


def parse_cv(filename: str, content: bytes) -> str:
    return parse_cv_document(filename, content)[0]


def parse_cv_document(filename: str, content: bytes) -> tuple[str, list[str]]:
    """Extract link targets separately so URLs never become skill evidence."""
    links = []
    def add_link(value):
        if isinstance(value, str) and len(value) <= 2048 and value not in links and len(links) < 200:
            links.append(value)

    suffix = Path(filename).suffix.lower()
    if suffix not in {'.pdf', '.docx'}:
        raise CVError('Choose a PDF or DOCX file.')
    if not content or len(content) > MAX_FILE_BYTES:
        raise CVError('CV must be non-empty and no larger than 10 MB.')
    try:
        if suffix == '.pdf':
            import pymupdf
            if not content.startswith(b'%PDF-'):
                raise CVError('The file is not a valid PDF.')
            with pymupdf.open(stream=content, filetype='pdf') as doc:
                if doc.needs_pass:
                    raise CVError('Password-protected PDFs are not supported. Upload an unlocked copy.')
                if len(doc) > MAX_PAGES:
                    raise CVError('CV must contain no more than 50 pages.')
                parts = []
                count = 0
                for page in doc:
                    for link in page.get_links():
                        add_link(link.get('uri'))
                    value = page.get_text('text', sort=True)
                    count += len(value)
                    if count > MAX_TEXT_CHARS:
                        raise CVError('CV text is too large.')
                    parts.append(value)
                text = '\n'.join(parts)
        else:
            from docx import Document
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if 'word/document.xml' not in archive.namelist():
                    raise CVError('The file is not a valid DOCX document.')
                if sum(info.file_size for info in archive.infolist()) > 25 * 1024 * 1024:
                    raise CVError('DOCX expanded contents are too large.')
                if any(info.flag_bits & 1 for info in archive.infolist()):
                    raise CVError('Encrypted DOCX files are not supported.')
            doc = Document(io.BytesIO(content))
            # Includes drawing/icon hyperlinks and header/footer relationships.
            from docx.opc.constants import RELATIONSHIP_TYPE as RT
            for part in doc.part.package.parts:
                for relationship in part.rels.values():
                    if relationship.reltype == RT.HYPERLINK and relationship.is_external:
                        add_link(relationship.target_ref)
            # Preserve paragraph/table order, including CV skills in table cells.
            from docx.oxml.ns import qn
            from docx.table import Table
            from docx.text.paragraph import Paragraph
            parts = []
            for element in doc.element.body:
                if element.tag == qn('w:p'):
                    parts.append(Paragraph(element, doc).text)
                elif element.tag == qn('w:tbl'):
                    parts.extend(' | '.join(cell.text for cell in row.cells) for row in Table(element, doc).rows)
            text = '\n'.join(parts)
    except CVError:
        raise
    except Exception as exc:
        raise CVError('Cannot read this CV. Upload a valid, unlocked PDF or DOCX.') from exc
    if len(text) > MAX_TEXT_CHARS:
        raise CVError('CV text is too large.')
    text = text.replace('\x00', '').replace('\r', '\n')
    if not text.strip():
        raise CVError('No readable text found. Scanned CVs need OCR before upload.')
    return text, links


HEADINGS = {
    'skills': {
        'skills', 'technical skills', 'technical expertise', 'technologies', 'core competencies',
        'clinical skills', 'medical skills', 'core skills', 'key skills', 'areas of expertise',
        'skills & competencies', 'skills and competencies', 'technical & clinical skills',
    },
    'projects': {
        'projects', 'selected projects', 'personal projects', 'academic projects', 'project experience',
        'selected academic & community projects', 'academic & community projects', 'community projects',
        'research projects',
    },
    'experience': {
        'experience', 'work experience', 'professional experience', 'employment', 'employment history',
        'clinical experience', 'medical experience', 'work history', 'internships', 'clinical rotations',
        'teaching experience', 'research experience',
    },
    'education': {'education', 'academic qualifications', 'qualifications'},
    'certifications': {
        'certifications', 'certificates', 'courses', 'training',
        'certifications & additional information', 'certifications and additional information',
        'licenses & certifications', 'certifications & training', 'additional information',
    },
    'summary': {'summary', 'professional summary', 'profile', 'about me', 'objective'},
}

CONTACT_LINE = re.compile(
    r'(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\+?\d[\d\s().-]{7,}\d|'
    r'^(?:address|phone|tel|mobile|email|e-mail|linkedin|github|portfolio|website|dob|nationality)\s*[:\-])',
    re.I,
)


def evidence_units(text):
    """Keep project blocks together and isolate personal/contact header lines from skill extraction."""
    section = 'personal_info'
    seen_heading = False
    block = []
    offset = 0
    start = 0
    units = []
    project_gap = False
    project_action = re.compile(r'\b(?:built|developed|implemented|designed|created|deployed|automated|integrated|maintained|tested|validated|prepared)\b', re.I)

    def flush():
        if block:
            units.append({'section': section, 'text': ' '.join(block), 'start': start})
            block.clear()

    for raw in text.splitlines(keepends=True):
        line = raw.strip().strip('•●▪- ').strip()
        heading = re.sub(r'\s+', ' ', line.lower().rstrip(':'))
        new_section = next((key for key, names in HEADINGS.items() if heading in names), None)
        if new_section:
            flush()
            section = new_section
            seen_heading = True
        elif not line:
            if section == 'projects':
                project_gap = True
            else:
                flush()
        elif not seen_heading:
            # Lines before the first heading belong to personal_info unless clearly a contact line vs headline.
            flush()
            start = offset
            block.append(line)
            flush()
        elif CONTACT_LINE.search(line):
            flush()
            units.append({'section': 'personal_info', 'text': line, 'start': offset})
        elif section == 'projects':
            numbered_title = re.match(r'^(?:\d{1,2}[.)]?\s+|project\s+\d)', line, re.I)
            # PDF extractors may insert blank lines between each visible line.
            heading_after_work = (project_gap and block and any(project_action.search(value) for value in block) and not project_action.search(line) and len(line) < 100 and not re.search(r'[|,:;.]', line))
            if numbered_title or heading_after_work:
                flush()
            project_gap = False
            if not block:
                start = offset
            block.append(line)
        else:
            flush()
            start = offset
            block.append(line)
            flush()
        offset += len(raw)
    flush()
    return units
