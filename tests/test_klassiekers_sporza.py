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

def test_get_file_mod_time(sporza_module, tmp_path):
    get_file_mod_time = sporza_module.get_file_mod_time

    # Test 1: File exists -> returns modification time
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    mod_time = get_file_mod_time(str(test_file))
    assert mod_time > 0

    # Test 2: File does not exist -> returns 0
    non_existent_file = tmp_path / "does_not_exist.txt"
    assert get_file_mod_time(str(non_existent_file)) == 0

    # Test 3: os.path.getmtime raises an exception (e.g. PermissionError) -> returns 0
    with patch("os.path.getmtime", side_effect=PermissionError("Mocked error")):
        assert get_file_mod_time(str(test_file)) == 0


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


def test_format_race_status(sporza_module):
    import pandas as pd
    import numpy as np

    format_race_status = sporza_module.format_race_status

    # Test NaN values
    assert format_race_status(pd.NA, 10) == ""
    assert format_race_status(np.nan, 10) == ""
    assert format_race_status(None, 10) == ""

    # Test special numeric codes
    assert format_race_status(999, 20) == "❌"
    assert format_race_status(888, 20) == "❓"
    assert format_race_status(777, 20) == " DNS"
    assert format_race_status(666, 20) == " DNF"
    assert format_race_status(555, 20) == " OTL"

    # Test values below or equal to limit
    assert format_race_status(1, 20) == "🟢 1"
    assert format_race_status(20, 20) == "🟢 20"

    # Test values above limit
    assert format_race_status(21, 20) == "21"
    assert format_race_status(100, 20) == "100"

    # Test string representations of numbers
    assert format_race_status("999", 20) == "❌"
    assert format_race_status("10.0", 20) == "🟢 10"
    assert format_race_status("21", 20) == "21"

    # Test float values
    assert format_race_status(888.0, 20) == "❓"
    assert format_race_status(5.5, 20) == "🟢 5" # float 5.5 becomes int 5
    assert format_race_status(25.9, 20) == "25" # float 25.9 becomes int 25

    # Test unparseable strings (error cases)
    assert format_race_status("DNS", 20) == ""
    assert format_race_status("DNF", 20) == ""
    assert format_race_status("Random string", 20) == ""
    assert format_race_status("", 20) == ""
