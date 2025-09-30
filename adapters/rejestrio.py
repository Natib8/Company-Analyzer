
import os
import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

UA = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; CompanyAnalyzer/1.0)")

def _get(url, delay=0.7):
    time.sleep(delay)
    return requests.get(url, headers={"User-Agent": UA}, timeout=30)

def _parse_company_page(soup):
    # Very defensive parsing — site layouts may change.
    data = {
        "name": None,
        "legal_form": None,
        "nip": None,
        "krs": None,
        "group_name": None,
        "employment": None,
        "revenue_value": None,
        "revenue_year": None,
        "source_name": "rejestr.io",
        "source_url": None,
        "rdf_docs_url": None,
    }

    # Title / Header
    h1 = soup.find("h1")
    if h1:
        data["name"] = h1.get_text(strip=True)

    # Common summary blocks (dl/dt/dd or table rows)
    text = soup.get_text(" ", strip=True)

    # Try to find NIP / KRS via regex on raw text
    m_nip = re.search(r"\bNIP[:\s]*([0-9]{10})\b", text)
    if m_nip:
        data["nip"] = m_nip.group(1)

    m_krs = re.search(r"\bKRS[:\s]*([0-9]{10})\b", text)
    if m_krs:
        data["krs"] = m_krs.group(1)

    # Forma prawna (heuristic: look for "Forma prawna" label)
    m_form = re.search(r"Forma prawna[:\s]*([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż.\- ]{3,60})", text)
    if m_form:
        data["legal_form"] = m_form.group(1).strip()

    # Grupa kapitałowa (if present)
    m_group = re.search(r"Grupa kapitałowa[:\s]*(.*?)(?:\s{2,}|$)", text)
    if m_group:
        val = m_group.group(1).strip()
        if val and val.lower() not in ("brak", "nie dotyczy", "—", "-"):
            data["group_name"] = val

    # Link do sprawozdań (jeśli na stronie jest sekcja z dokumentami)
    # Często rejestr.io linkuje do eKRS RDF lub PDF — szukamy linków ze słowem "sprawozdania" lub .pdf
    rdf_link = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        label = a.get_text(" ", strip=True).lower()
        if ("sprawozdania" in label or "sprawozdanie" in label) and ("krs" in href or "ms.gov" in href or "ekrs" in href):
            rdf_link = href
            break
    data["rdf_docs_url"] = rdf_link

    return data

def lookup_by_nip(nip: str):
    nip = re.sub(r"\D+", "", nip or "")
    if not nip or len(nip) != 10:
        return None
    url = f"https://rejestr.io/nip/{nip}"
    r = _get(url)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    out = _parse_company_page(soup)
    out["source_url"] = url
    return out

def lookup_by_name(name: str):
    name = (name or "").strip()
    if not name:
        return None
    q = urllib.parse.quote_plus(name)
    search_url = f"https://rejestr.io/szukaj?query={q}"
    r = _get(search_url)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")

    # Try pick first reasonable result link pointing to a company page
    first_link = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/krs/") or href.startswith("/nip/") or href.startswith("/regon/"):
            first_link = urllib.parse.urljoin("https://rejestr.io", href)
            break
    if not first_link:
        return None

    r2 = _get(first_link)
    if r2.status_code != 200:
        return None
    soup2 = BeautifulSoup(r2.text, "lxml")
    out = _parse_company_page(soup2)
    out["source_url"] = first_link
    return out
