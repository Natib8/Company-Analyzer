import sys
import re
import pandas as pd

# Użycie: python prep_input.py input_companies.csv cleaned_input.csv

inp = sys.argv[1]
out = sys.argv[2]

df = pd.read_csv(inp, dtype=str, keep_default_na=False)

# 1) Mapowanie nagłówków -> 'nazwa', 'nip' (elastycznie, bez względu na format)
cols = {c.lower().strip(): c for c in df.columns}

def pick(colnames, fallbacks):
    for f in fallbacks:
        key = f.lower().strip()
        if key in cols:
            return cols[key]
    # szukaj zawiera/regex
    lc = {c.lower().strip(): c for c in df.columns}
    for k, v in lc.items():
        if any(pat in k for pat in colnames):
            return v
    return None

col_name = pick(["account name","nazwa","company","firma"], ["Account Name","Nazwa"])
col_nip  = pick(["nip","vat"], ["NIP*","NIP"])

if not col_name:
    raise SystemExit("Nie znalazłam kolumny z nazwą (np. 'Account Name' / 'Nazwa').")

# 2) Zbuduj wynikową tabelę tylko z wymaganymi kolumnami
out_df = pd.DataFrame()
out_df["nazwa"] = df[col_name].astype(str).str.strip()

if col_nip and col_nip in df.columns:
    nip_raw = df[col_nip].astype(str)
else:
    nip_raw = pd.Series([""]*len(out_df))

# 3) Normalizacja NIP: tylko cyfry, 10 cyfr → zostaw; inaczej puste
def norm_nip(x):
    d = re.sub(r"\D+", "", str(x))
    return d if len(d) == 10 else ""

out_df["nip"] = nip_raw.map(norm_nip)

# 4) Filtry jakości:
# - usuń puste nazwy
# - wytnij wiersze typu "Wypełnienie formularza ..."
mask_bad = out_df["nazwa"].str.strip().eq("") | out_df["nazwa"].str.contains(r"wypełnienie formularza", case=False, na=False)
out_df = out_df[~mask_bad]

# 5) Dedup (po nazwie + nip)
out_df = out_df.drop_duplicates(subset=["nazwa","nip"]).reset_index(drop=True)

# 6) Zapis
out_df.to_csv(out, index=False, encoding="utf-8-sig")
print(f"OK → {out} (wierszy: {len(out_df)})")
