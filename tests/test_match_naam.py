import pytest
from app_utils.name_matching import normalize_name_logic, match_naam_slim, match_uitslag_naam

def test_normalize_name_logic():
    assert normalize_name_logic("Tadej Pogačar") == "tadej pogacar"
    assert normalize_name_logic("Wout van Aert") == "wout van aert"
    assert normalize_name_logic("Mathieu van der Poel") == "mathieu van der poel"
    assert normalize_name_logic("Arnaud De Lie") == "arnaud de lie"
    assert normalize_name_logic(None) == ""

def test_match_naam_slim_exact_match():
    # Setup mock dictionary
    dict_met_namen = {
        "remco evenepoel": "Remco Evenepoel",
        "primoz roglic": "Primož Roglič",
        "casper pedersen": "Casper Pedersen",
        "mads pedersen": "Mads Pedersen"
    }

    # Exact normalized match
    assert match_naam_slim("Remco Evenepoel", dict_met_namen) == "Remco Evenepoel"
    assert match_naam_slim("Primoz Roglic", dict_met_namen) == "Primož Roglič"
    assert match_naam_slim("Casper Pedersen", dict_met_namen) == "Casper Pedersen"

def test_match_naam_slim_bekende_gevallen():
    # Setup mock dictionary containing canonical targets
    dict_met_namen = {
        "jasper philipsen": "Jasper Philipsen",
        "mads pedersen": "Mads Pedersen",
        "thomas pidcock": "Tom Pidcock",
        "wout van aert": "Wout van Aert",
        "mathieu van der poel": "Mathieu van der Poel",
        "tadej pogacar": "Tadej Pogačar",
        "arnaud de lie": "Arnaud De Lie"
    }

    # These contain the bekende gevallen keys
    assert match_naam_slim("Philipsen", dict_met_namen) == "Jasper Philipsen"
    assert match_naam_slim("J. Philipsen", dict_met_namen) == "Jasper Philipsen"
    assert match_naam_slim("Pedersen", dict_met_namen) == "Mads Pedersen"
    assert match_naam_slim("M. Pedersen", dict_met_namen) == "Mads Pedersen"
    assert match_naam_slim("Pidcock", dict_met_namen) == "Tom Pidcock"
    assert match_naam_slim("Van Aert", dict_met_namen) == "Wout van Aert"
    assert match_naam_slim("Van der Poel", dict_met_namen) == "Mathieu van der Poel"
    assert match_naam_slim("Pogacar", dict_met_namen) == "Tadej Pogačar"
    assert match_naam_slim("De Lie", dict_met_namen) == "Arnaud De Lie"

def test_match_naam_slim_fuzzy_match():
    dict_met_namen = {
        "jonas vingegaard": "Jonas Vingegaard",
        "matej mohoric": "Matej Mohorič"
    }

    # Should fuzzy match with >= 75 score
    assert match_naam_slim("J. Vingegaard", dict_met_namen) == "Jonas Vingegaard"
    assert match_naam_slim("Matej Mohoricc", dict_met_namen) == "Matej Mohorič"

def test_match_naam_slim_no_match():
    dict_met_namen = {
        "jonas vingegaard": "Jonas Vingegaard",
        "matej mohoric": "Matej Mohorič"
    }

    # Completely different name should return the original input
    assert match_naam_slim("Biniam Girmay", dict_met_namen) == "Biniam Girmay"

def test_match_uitslag_naam_bekende_gevallen():
    alle_renners = [
        "Jasper Philipsen",
        "Mads Pedersen",
        "Tom Pidcock",
        "Wout van Aert",
        "Mathieu van der Poel",
        "Tadej Pogačar",
        "Arnaud De Lie"
    ]

    assert match_uitslag_naam("J. Philipsen", alle_renners) == "Jasper Philipsen"
    assert match_uitslag_naam("Van Aert", alle_renners) == "Wout van Aert"

def test_match_uitslag_naam_fuzzy_match():
    alle_renners = [
        "Jonas Vingegaard",
        "Matej Mohorič"
    ]

    assert match_uitslag_naam("J. Vingegaard", alle_renners) == "Jonas Vingegaard"

def test_match_uitslag_naam_no_match():
    alle_renners = [
        "Jonas Vingegaard",
        "Matej Mohorič"
    ]

    assert match_uitslag_naam("Biniam Girmay", alle_renners) == "Biniam Girmay"

def test_match_uitslag_naam_edge_cases():
    alle_renners = [
        "Casper Pedersen",
        "Mads Pedersen"
    ]
    # "Casper Pedersen" has "pedersen" in it, but shouldn't match "Mads Pedersen" since we have a direct match.
    assert match_uitslag_naam("Casper Pedersen", alle_renners) == "Casper Pedersen"
