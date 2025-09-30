
from rapidfuzz import fuzz

def normalize(s: str) -> str:
    return (s or "").strip()

def name_score(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return int(fuzz.WRatio(a, b))
