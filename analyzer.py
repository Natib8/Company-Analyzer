
import argparse
from datetime import datetime, timezone
from typing import Dict, Any

import pandas as pd
from utils.match import normalize

from adapters import rejestrio, krs, rdf_sprawozdania

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

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def safe(x, fallback="brak danych"):
    if x is None or (isinstance(x, str) and not x.strip()):
        return fallback
    return x

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

    df = pd.read_csv(args.input_csv)
    rows_out = []
    for _, r in df.iterrows():
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
