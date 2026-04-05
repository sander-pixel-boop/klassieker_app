import sys
from unittest.mock import patch
import importlib.util
import streamlit as st

st.session_state["ingelogde_speler"] = "test"
st.secrets = {"SUPABASE_URL": "http://mock", "SUPABASE_KEY": "mock"}

with patch("supabase.create_client") as mock_create_client:
    spec = importlib.util.spec_from_file_location("sporza", "pages/Klassiekers - Sporza.py")
    sporza = importlib.util.module_from_spec(spec)
    sys.modules["sporza"] = sporza
    spec.loader.exec_module(sporza)

bepaal_klassieker_type = sporza.bepaal_klassieker_type
try:
    print("Test 1:", bepaal_klassieker_type({'SPR': 90, 'COB': 0, 'HLL': 0}))
    print("Test 2:", bepaal_klassieker_type({'SPR': 0, 'COB': 90, 'HLL': 0}))
    print("Test 3:", bepaal_klassieker_type({}))
    print("Test 4:", bepaal_klassieker_type({'SPR': 'a', 'COB': 'b', 'HLL': 'c'}))
except Exception as e:
    import traceback
    traceback.print_exc()
