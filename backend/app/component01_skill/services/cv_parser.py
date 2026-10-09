"""Bounded PDF/DOCX parsing; uploaded bytes are never saved to disk."""
import io
import re
import zipfile
from pathlib import Path
from ..config import MAX_FILE_BYTES, MAX_PAGES, MAX_TEXT_CHARS


class CVError(ValueError):
    pass


def parse_cv(filename: str, content: bytes) -> str:
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
    return text


HEADINGS = {
    'skills': {'skills', 'technical skills', 'technical expertise', 'technologies', 'core competencies'},
    'projects': {'projects', 'selected projects', 'personal projects', 'academic projects', 'project experience'},
    'experience': {'experience', 'work experience', 'professional experience', 'employment', 'employment history'},
    'education': {'education', 'academic qualifications', 'qualifications'},
    'certifications': {'certifications', 'certificates', 'courses', 'training'},
    'summary': {'summary', 'professional summary', 'profile', 'about me', 'objective'},
}


def evidence_units(text):
    """Keep project blocks together so technology lists accompany their actions."""
    section = 'other'
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
        elif not line:
            if section == 'projects':
                project_gap = True
            else:
                flush()
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
