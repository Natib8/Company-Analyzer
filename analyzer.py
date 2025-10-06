import argparse
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

import pandas as pd

# upewnij się, że root repo jest w ścieżce importów
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.match import normalize
import adapters.krs as krs
import adapters.rejestrio as rejestrio
import adapters.rdf_sprawozdania as rdf_sprawozdania

OUT_COLUMNS = [
    "Nazwa",
    "Prawidłowa nazwa",
    "Forma prawna",
    "NIP",
    "Przychody",
    "Zatrudnienie",
    "Grupa kapitałowa",
    "Nazwa Grupy kapitałowej",
    "Źródło"
]

# ---------- helpers: input mapping/cleaning ----------

NAME_HINTS = ["nazwa", "account name", "company", "firma"]
NIP_HINTS  = ["nip", "vat"]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def safe(x, fallback="brak danych"):
    if x is None or (isinstance(x, str) and not x.strip()):
        return fallback
    return x

def _pick_column(columns, hints) -> Tuple[str, str] | Tuple[None, None]:
    """Zwraca (oryginalna_nazwa_kolumny, dolna_nazwa) dla pierwszego dopasowania po podpowiedziach."""
    lower_map = {c.lower().strip(): c for c in columns}
    # ideal: pełny match
    for h in hints:
        if h in lower_map:
            return lower_map[h], h
    # fuzzy: zawiera
    for c in columns:
        lc = c.lower().strip()
        if any(h in lc for h in hints):
            return c, lc
    return None, None

def _norm_nip(x: str) -> str:
    d = re.sub(r"\D+", "", str(x or ""))
    return d if len(d) == 10 else ""

def load_input_any(input_csv: str) -> pd.DataFrame:
    """
    Czyta dowolny CSV i zwraca DataFrame z kolumnami: nazwa, nip (nip może być pusty).
    - mapuje nagłówki (np. 'Account Name' -> 'nazwa', 'NIP*' -> 'nip')
    - czyści NIP do 10 cyfr
    - usuwa puste nazwy i 'Wypełnienie formularza ...'
    - deduplikuje po (nazwa, nip)
    """
    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False)

    col_name, _ = _pick_column(df.columns, NAME_HINTS)
    col_nip, _  = _pick_column(df.columns, NIP_HINTS)

    if not col_name:
        raise SystemExit("Nie znalazłam kolumny z nazwą spółki (np. 'Account Name' / 'Nazwa').")

    out = pd.DataFrame()
    out["nazwa"] = df[col_name].astype(str).str.strip()

    if col_nip and col_nip in df.columns:
        out["nip"] = df[col_nip].map(_norm_nip)
    else:
        out["nip"] = ""

    # filtry jakości
    mask_bad = (
        out["nazwa"].str.strip().eq("") |
        out["nazwa"].str.contains(r"wypełnienie formularza", case=False, na=False)
    )
    out = out[~mask_bad]

    # dedup
    out = out.drop_duplicates(subset=["nazwa", "nip"]).reset_index(drop=True)
    return out

# ---------- core ----------

def resolve_company(original_name: str, nip: str) -> Dict[str, Any]:
    original_name_norm = normalize(original_name)
    result = {
        "original_name": original_name_norm,
        "name": None,
        "legal_form": None,
        "nip": nip.strip() if isinstance(nip, str) else None,
        "group": None,
        "group_name": None,
        "employment": None,
        "revenue_value": None,
        "revenue_year": None,
        "source_name": None,
        "source_url": None,
        "sources_joined": ""
    }

    data = None
    if result["nip"]:
        data = krs.lookup_by_nip(result["nip"]) or rejestrio.lookup_by_nip(result["nip"])
    if not data and original_name_norm:
        data = krs.lookup_by_name(original_name_norm) or rejestrio.lookup_by_name(original_name_norm)

    if data:
        result.update(data)
        finances = None
        if data.get('rdf_docs_url'):
            from adapters.rdf_sprawozdania import latest_financials_from_docs_url
            finances = latest_financials_from_docs_url(data.get('rdf_docs_url'))
        if finances:
            result["revenue_value"] = finances.get("revenue_value") or result.get("revenue_value")
            result["revenue_year"]  = finances.get("revenue_year")  or result.get("revenue_year")
            result["employment"]    = finances.get("employment")    or result.get("employment")

        if not result.get("sources_joined"):
            src_name = safe(result.get("source_name"), "")
            src_url  = safe(result.get("source_url"), "")
            src = f"{src_name} ({src_url})".strip()
            result["sources_joined"] = src if src != "()" else ""

    return result

def write_output(df_out: pd.DataFrame, output_path: str):
    if output_path.lower().endswith(".xlsx"):
        df_out.to_excel(output_path, index=False)
    else:
        df_out.to_csv(output_path, index=False, encoding="utf-8-sig")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_csv")
    ap.add_argument("output_file")  # CSV lub XLSX
    args = ap.parse_args()

    # <<< NEW: wczytaj dowolny CSV i przerób go na (nazwa, nip) >>>
    df_clean = load_input_any(args.input_csv)

    rows_out = []
    for _, r in df_clean.iterrows():
        nazwa = str(r.get("nazwa") or "").strip()
        nip = str(r.get("nip") or "").strip()
        resolved = resolve_company(nazwa, nip)

        rows_out.append({
            "Nazwa": nazwa or "brak danych",
            "Prawidłowa nazwa": resolved.get("name") or "brak danych",
            "Forma prawna": resolved.get("legal_form") or "brak danych",
            "NIP": resolved.get("nip") or (nip if nip else "brak danych"),
            "Przychody": (f"{resolved.get('revenue_value')} (rok {resolved.get('revenue_year')})"
                         if resolved.get("revenue_value") else "brak danych"),
            "Zatrudnienie": resolved.get("employment") or "brak danych",
            "Grupa kapitałowa": "TAK" if resolved.get("group") else "brak",
            "Nazwa Grupy kapitałowej": resolved.get("group_name") or "brak danych",
            "Źródło": resolved.get("sources_joined") or "brak danych"
        })

    out = pd.DataFrame(rows_out, columns=OUT_COLUMNS)
    write_output(out, args.output_file)
    print(f"Wrote: {args.output_file}")

if __name__ == "__main__":
    main()
