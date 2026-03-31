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
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 0, 'HLL': 0}) == 'Sprinter'

    # Test Kasseien
    assert bepaal_klassieker_type({'SPR': 0, 'COB': 90, 'HLL': 0}) == 'Kasseien'

    # Test Heuvel
    assert bepaal_klassieker_type({'SPR': 0, 'COB': 0, 'HLL': 90}) == 'Heuvel'

    # Test Missing Keys (should fall back to 0, resulting in a tie of 0 > 0 which is False -> None)
    assert bepaal_klassieker_type({}) is None

    # Test Invalid Types (should be caught by except and result in 0, 0, 0 -> None)
    assert bepaal_klassieker_type({'SPR': 'a', 'COB': 'b', 'HLL': 'c'}) is None

    # Test Ties (returns None because > is strictly greater)
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 90, 'HLL': 0}) is None
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 0, 'HLL': 90}) is None
    assert bepaal_klassieker_type({'SPR': 0, 'COB': 90, 'HLL': 90}) is None
    assert bepaal_klassieker_type({'SPR': 90, 'COB': 90, 'HLL': 90}) is None

    # Test String values that can be parsed as int
    assert bepaal_klassieker_type({'SPR': '90', 'COB': '80', 'HLL': '70'}) == 'Sprinter'
    assert bepaal_klassieker_type({'SPR': '70', 'COB': '90', 'HLL': '80'}) == 'Kasseien'
    assert bepaal_klassieker_type({'SPR': '70', 'COB': '80', 'HLL': '90'}) == 'Heuvel'

    # Test exact equality edge cases
    assert bepaal_klassieker_type({'SPR': 0, 'COB': 0, 'HLL': 0}) is None
