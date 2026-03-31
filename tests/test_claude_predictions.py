import pytest
from claude_predictions import _fuzzy_resolve

def test_fuzzy_resolve_exact_match():
    valid_names = ['Tadej Pogačar', 'Wout van Aert']
    assert _fuzzy_resolve('Tadej Pogačar', valid_names) == 'Tadej Pogačar'

def test_fuzzy_resolve_missing_accents():
    valid_names = ['Tadej Pogačar', 'João Almeida']
    assert _fuzzy_resolve('Tadej Pogacar', valid_names) == 'Tadej Pogačar'
    assert _fuzzy_resolve('Joao Almeida', valid_names) == 'João Almeida'

def test_fuzzy_resolve_reversed_names():
    valid_names = ['Remco Evenepoel']
    assert _fuzzy_resolve('Evenepoel Remco', valid_names) == 'Remco Evenepoel'

def test_fuzzy_resolve_partial_match():
    valid_names = ['J. Vingegaard', 'Biniam Girmay']
    assert _fuzzy_resolve('Vingegaard', valid_names) == 'J. Vingegaard'
    assert _fuzzy_resolve('Girmay', valid_names) == 'Biniam Girmay'

def test_fuzzy_resolve_no_match():
    valid_names = ['Tadej Pogačar', 'Wout van Aert']
    assert _fuzzy_resolve('Mathieu van der Poel', valid_names) is None
