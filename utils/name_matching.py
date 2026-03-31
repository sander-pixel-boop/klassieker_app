import unicodedata
from thefuzz import process, fuzz

def normalize_name_logic(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def match_naam_slim(naam, dict_met_namen):
    naam_norm = normalize_name_logic(naam)
    lijst_met_namen = list(dict_met_namen.keys())

    bekende_gevallen = {
        "philipsen": "jasper philipsen",
        "pedersen": "mads pedersen",
        "pidcock": "thomas pidcock",
        "van aert": "wout van aert",
        "van der poel": "mathieu van der poel",
        "pogacar": "tadej pogacar",
        "de lie": "arnaud de lie"
    }

    for key, correct in bekende_gevallen.items():
        if key in naam_norm:
            for target in lijst_met_namen:
                if correct in target:
                    return dict_met_namen[target]

    if naam_norm in lijst_met_namen:
        return dict_met_namen[naam_norm]

    bests = process.extractBests(naam_norm, lijst_met_namen, scorer=fuzz.token_set_ratio, limit=5)
    if bests and bests[0][1] >= 75:
        top_score = bests[0][1]
        candidates = [b[0] for b in bests if b[1] >= top_score - 3]
        candidates.sort(key=lambda x: (abs(len(x) - len(naam_norm)), -fuzz.ratio(naam_norm, x)))
        return dict_met_namen[candidates[0]]

    return naam

def match_uitslag_naam(naam, alle_renners):
    naam_norm = normalize_name_logic(naam)
    bekende_gevallen = {
        "philipsen": "jasper philipsen",
        "pedersen": "mads pedersen",
        "pidcock": "thomas pidcock",
        "van aert": "wout van aert",
        "van der poel": "mathieu van der poel",
        "pogacar": "tadej pogacar",
        "de lie": "arnaud de lie"
    }

    for key, correct in bekende_gevallen.items():
        if key in naam_norm:
            for target in alle_renners:
                if correct in normalize_name_logic(target):
                    return target

    bests = process.extractBests(naam_norm, alle_renners, scorer=fuzz.token_set_ratio, limit=5)
    if bests and bests[0][1] >= 75:
        top_score = bests[0][1]
        candidates = [b[0] for b in bests if b[1] >= top_score - 3]
        candidates.sort(key=lambda x: (abs(len(normalize_name_logic(x)) - len(naam_norm)), -fuzz.ratio(naam_norm, normalize_name_logic(x))))
        return candidates[0]
    return naam
