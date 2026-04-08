import pytest
import sys
import streamlit as st
import importlib.util
from unittest.mock import patch

@pytest.fixture(scope="module")
def sporza_module():
    # Setup state before importing
    st.session_state["ingelogde_speler"] = "test"
    st.secrets = {"SUPABASE_URL": "http://mock", "SUPABASE_KEY": "mock"}

    # Mock create_client to avoid actual network calls during import
    with patch("supabase.create_client") as mock_create_client:
        spec = importlib.util.spec_from_file_location("sporza", "pages/Klassiekers - Sporza.py")
        sporza = importlib.util.module_from_spec(spec)
        sys.modules["sporza"] = sporza
        spec.loader.exec_module(sporza)
        return sporza

def test_bepaal_klassieker_type(sporza_module):
    bepaal_klassieker_type = sporza_module.bepaal_klassieker_type

    # Test Sprinter
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 0, 'HLL': 0}) == 'Sprint'

    # Test Kasseien
    assert bepaal_klassieker_type({'SPR': 0, 'COB': 90, 'HLL': 0}) == 'Kassei'

    # Test Heuvel
    assert bepaal_klassieker_type({'SPR': 0, 'COB': 0, 'HLL': 90}) == 'Heuvel'

    # Test Missing Keys (should fall back to 0, resulting in a tie of 0 > 0 which is False -> None)
    assert bepaal_klassieker_type({}) == 'Onbekend'

    # Test Invalid Types (should be caught by except and result in 0, 0, 0 -> None)
    assert bepaal_klassieker_type({'SPR': 'a', 'COB': 'b', 'HLL': 'c'}) == 'Onbekend'

    # Test Ties (returns None because > is strictly greater)
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 90, 'HLL': 0}) == 'Kassei / Sprint'
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 0, 'HLL': 90}) == 'Heuvel / Sprint'
    assert bepaal_klassieker_type({'SPR': 0, 'COB': 90, 'HLL': 90}) == 'Kassei / Heuvel'
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 90, 'HLL': 90}) == 'Allround / Multispecialist'

    # Test String values that can be parsed as int
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 80, 'HLL': 70}) == 'Sprint'
    assert bepaal_klassieker_type({'SPR': 70, 'COB': 90, 'HLL': 80}) == 'Kassei'
    assert bepaal_klassieker_type({'SPR': 70, 'COB': 80, 'HLL': 90}) == 'Heuvel'

    # Test exact equality edge cases
    assert bepaal_klassieker_type({'SPR': 0, 'COB': 0, 'HLL': 0}) == 'Onbekend'

def test_get_numeric_status(sporza_module):
    get_numeric_status = sporza_module.get_numeric_status

    # Tests for when race has NOT been ridden yet (is_verreden=False)
    assert get_numeric_status(is_on_startlist=False, is_starter=False, is_verreden=False) == 999
    assert get_numeric_status(is_on_startlist=True, is_starter=False, is_verreden=False) == 888
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=False) == 888

    # Tests for when race HAS been ridden (is_verreden=True)

    # Valid digit strings
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str="1") == 1.0
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str=" 42 ") == 42.0

    # Special codes (DNS, DNF, OTL)
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str="DNS") == 777
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str="dns ") == 777
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str="DNF") == 666
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str="dnf") == 666
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str="OTL") == 555

    # Unparseable strings not matching special codes
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str="UNKNOWN") == 999

    # Empty or None rank_str (falls back to starter check)
    assert get_numeric_status(is_on_startlist=True, is_starter=True, is_verreden=True, rank_str="") == 666
    assert get_numeric_status(is_on_startlist=True, is_starter=False, is_verreden=True, rank_str=None) == 777
