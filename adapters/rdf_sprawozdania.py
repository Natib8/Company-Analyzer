
import os
import re
import time
import requests
from bs4 import BeautifulSoup

UA = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; CompanyAnalyzer/1.0)")

def latest_financials_from_docs_url(url: str):
    if not url:
        return None
    time.sleep(0.7)
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    except Exception:
        return None
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "lxml")
    # Collect candidate PDF links with year hints
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        label = a.get_text(" ", strip=True)
        if href.lower().endswith(".pdf"):
            year_m = re.search(r"(20[0-9]{2}|19[0-9]{2})", label + " " + href)
            year = int(year_m.group(1)) if year_m else None
            full = requests.compat.urljoin(url, href)
            candidates.append((year or 0, full))

    if not candidates:
        return None
    # Pick newest by year (if detected), else last item
    candidates.sort(key=lambda x: x[0], reverse=True)
    pdf_url = candidates[0][1]

    # Download PDF
    time.sleep(0.7)
    rr = requests.get(pdf_url, headers={"User-Agent": UA}, timeout=60)
    if rr.status_code != 200 or not rr.content:
        return None

    # Parse PDF text to extract revenue & optional employment
    from parsers.financials_pdf import extract_revenue_and_employment
    fin = extract_revenue_and_employment(rr.content) or {}
    fin["pdf_url"] = pdf_url
    return fin
