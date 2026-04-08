import time
import functools
import unicodedata
import random

class process:
    @staticmethod
    def extractBests(query, choices, scorer=None, limit=3):
        return [(c, 80) for c in choices[:limit]]

class fuzz:
    token_set_ratio = None

@functools.lru_cache(maxsize=1024)
def normalize_name(text):
    if not isinstance(text, str): return ""
    text = text.lower().strip()
    return "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))

@functools.lru_cache(maxsize=2048)
def match_naam_cached_original(naam, alle_renners_tuple):
    naam_norm = normalize_name(naam)
    bekende = {
        "pogacar": "tadej pogačar", "van der poel": "mathieu van der poel",
        "philipsen": "jasper philipsen", "van aert": "wout van aert",
        "pidcock": "thomas pidcock", "de lie": "arnaud de lie"
    }
    for key, correct in bekende.items():
        if key in naam_norm:
            for r in alle_renners_tuple:
                if correct in normalize_name(r): return r

    norm_lijst = {normalize_name(r): r for r in alle_renners_tuple}
    if naam_norm in norm_lijst: return norm_lijst[naam_norm]

    bests = process.extractBests(naam_norm, list(norm_lijst.keys()), scorer=fuzz.token_set_ratio, limit=3)
    if bests and bests[0][1] >= 75:
        return norm_lijst[bests[0][0]]
    return naam

@functools.lru_cache(maxsize=32)
def get_norm_lijst(alle_renners_tuple):
    return {normalize_name(r): r for r in alle_renners_tuple}

@functools.lru_cache(maxsize=2048)
def match_naam_cached_optimized(naam, alle_renners_tuple):
    naam_norm = normalize_name(naam)
    bekende = {
        "pogacar": "tadej pogačar", "van der poel": "mathieu van der poel",
        "philipsen": "jasper philipsen", "van aert": "wout van aert",
        "pidcock": "thomas pidcock", "de lie": "arnaud de lie"
    }
    norm_lijst = get_norm_lijst(alle_renners_tuple)
    for key, correct in bekende.items():
        if key in naam_norm:
            for norm_r, r in norm_lijst.items():
                if correct in norm_r: return r

    if naam_norm in norm_lijst: return norm_lijst[naam_norm]

    bests = process.extractBests(naam_norm, list(norm_lijst.keys()), scorer=fuzz.token_set_ratio, limit=3)
    if bests and bests[0][1] >= 75:
        return norm_lijst[bests[0][0]]
    return naam

alle_renners = [f"Renner {i}" for i in range(1000)]
namen_to_match = [f"Renner {i}" for i in range(2000)] + ["Unknown Renner"]

t0 = time.time()
for n in namen_to_match:
    match_naam_cached_original(n, tuple(alle_renners))
t1 = time.time()
for n in namen_to_match:
    match_naam_cached_optimized(n, tuple(alle_renners))
t2 = time.time()

print(f"Original: {t1-t0:.4f}s")
print(f"Optimized: {t2-t1:.4f}s")
