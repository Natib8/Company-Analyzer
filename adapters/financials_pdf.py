
import io
import re
import pdfplumber

REVENUE_PATTERNS = [
    r"Przychody\s+netto\s+ze\s+sprzedaży[^\n]*?([\d\s\.,]+)",
    r"Przychody\s+ze\s+sprzedaży\s+netto[^\n]*?([\d\s\.,]+)",
    r"Przychody\s+netto[^\n]*?([\d\s\.,]+)",
]

EMPLOYMENT_PATTERNS = [
    r"Średnioroczne\s+zatrudnienie[^\n]*?(\d{1,6})",
    r"Zatrudnienie[^\n]*?(\d{1,6})\s*(?:osób|etaty|FTE)",
]

YEAR_PATTERNS = [
    r"za\s+rok\s+zakończony\s+([0-9]{4})",
    r"rok\s+obrotowy\s+([0-9]{4})",
    r"za\s+([0-9]{4})\s*rok",
]

def _first_number(s):
    if not s:
        return None
    x = s.replace(" ", "").replace("\u00a0", "")
    x = x.replace(",", ".")
    # extract number with optional thousands separators
    m = re.search(r"[0-9]+(?:\.[0-9]{3})*(?:,[0-9]+)?|[0-9]+(?:\.[0-9]+)?", s.replace("\u00a0"," "))
    return m.group(0) if m else s

def extract_revenue_and_employment(pdf_bytes: bytes):
    text_joined = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages[:10]:  # first pages usually contain P&L
            try:
                t = page.extract_text() or ""
                text_joined += "\n" + t
            except Exception:
                continue

    text = text_joined

    revenue = None
    for pat in REVENUE_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            revenue = _first_number(m.group(1))
            break

    employment = None
    for pat in EMPLOYMENT_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            employment = m.group(1)
            break

    year = None
    for pat in YEAR_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            year = m.group(1)
            break

    out = {}
    if revenue:
        out["revenue_value"] = revenue
    if employment:
        out["employment"] = employment
    if year:
        out["revenue_year"] = year
    return out
