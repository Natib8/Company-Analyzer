
# Bulk Company Analyzer (PL)

Automatyczna analiza polskich spółek (NIP/nazwa) z publicznych, wiarygodnych źródeł.
Zasady: **nie wymyślamy danych**, „brak danych” jeśli brak potwierdzenia, **zawsze podajemy źródło**.

**Wejście:** `input_companies.csv` (kolumny min. `id`, `nazwa`, opcjonalnie `nip`)  
**Wyjście:** `output_companies.csv` **i** `output_companies.xlsx` z kolumnami:
`Nazwa`, `Prawidłowa nazwa`, `Forma prawna`, `NIP`, `Przychody`, `Zatrudnienie`, `Grupa kapitałowa`,
`Nazwa Grupy kapitałowej`, `Źródło`.

> Adaptery do źródeł są *szablonami* — uzupełnij je realnymi zapytaniami/parsowaniem w ramach ToS i prawa.  
> Workflow GitHub Actions wysyła gotowy XLSX **mailem** (SMTP), bez limitów wierszy.

## Jak używać (lokalnie)
```bash
pip install -r company-analyzer/requirements.txt
python company-analyzer/analyzer.py company-analyzer/input_companies.csv company-analyzer/output_companies.xlsx
```

## GitHub Actions — email z XLSX
Workflow: `.github/workflows/company-analyzer.yml`

Ustaw sekrety repo (Settings → Secrets and variables → Actions → New repository secret):
- `SMTP_SERVER` — np. `smtp.gmail.com`
- `SMTP_PORT` — np. `587`
- `SMTP_USERNAME` — login do SMTP
- `SMTP_PASSWORD` — hasło/aplikacyjne
- `EMAIL_FROM` — adres nadawcy
- `EMAIL_TO` — adres odbiorcy (np. Twój)

Uruchom z zakładki **Actions** → **Company Analyzer** → **Run workflow**.

## Źródła (zalecane)
- KRS/eKRS (Ministerstwo Sprawiedliwości) — dane rejestrowe + RDF (Repozytorium Dokumentów Finansowych).
- rejestr.io — agregacja linków do oficjalnych rejestrów (bez Aleo).
- Sprawozdania finansowe (PDF/ZIP) — do pozyskania przychodów netto i potencjalnie zatrudnienia.
- GUS/REGON (opcjonalnie) — dane uzupełniające (jeśli dostępne publicznie).

## Zasady przetwarzania
- Przetwarzamy **całość pliku** — brak arbitralnych limitów (100%, niezależnie od liczby rekordów).
- Jeśli nazwa wejściowa ≠ oficjalna, wpisujemy oficjalną w kolumnie **Prawidłowa nazwa**.
- `Źródło` zawiera nazwę źródła i (jeśli dostępny) URL.
- Respektujemy robots.txt i ToS serwisów; dodajemy opóźnienia i cache, jeśli to konieczne.

## Struktura
```
company-analyzer/
  adapters/
    krs.py
    rejestrio.py
    rdf_sprawozdania.py
  parsers/
    financials_pdf.py
  utils/
    match.py
  analyzer.py
  requirements.txt
  input_companies.csv
.github/
  workflows/
    company-analyzer.yml
README.md
```
