import pytest
import sys
import os
import streamlit as st
import importlib.util
from unittest.mock import patch, mock_open

@pytest.fixture(scope="module")
def giro_bouwer_module():
    # Setup state before importing
    st.session_state["ingelogde_speler"] = "test"
    st.secrets = {"SUPABASE_URL": "http://mock", "SUPABASE_KEY": "mock"}

    with patch("supabase.create_client"):
        spec = importlib.util.spec_from_file_location("sporza_giro", "pages/Sporza/Giro/Team_Bouwer.py")
        sporza_giro = importlib.util.module_from_spec(spec)
        sys.modules["sporza_giro"] = sporza_giro

        # Stop execution before rendering
        with patch("streamlit.tabs", side_effect=Exception("Stop Execution")):
            try:
                spec.loader.exec_module(sporza_giro)
            except Exception as e:
                if str(e) != "Stop Execution":
                    raise
        return sporza_giro

def test_get_clickable_image_html_success_png(giro_bouwer_module):
    get_html = giro_bouwer_module.get_clickable_image_html

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=b"dummy_image_data")):
            html = get_html("test.png", "Fallback", "http://link")
            assert "data:image/png;base64,ZHVtbXlfaW1hZ2VfZGF0YQ==" in html
            assert "href=\"http://link\"" in html

def test_get_clickable_image_html_success_jpeg(giro_bouwer_module):
    get_html = giro_bouwer_module.get_clickable_image_html

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=b"dummy_image_data")):
            html = get_html("test.jpg", "Fallback", "http://link")
            assert "data:image/jpeg;base64,ZHVtbXlfaW1hZ2VfZGF0YQ==" in html
            assert "href=\"http://link\"" in html

def test_get_clickable_image_html_file_not_found(giro_bouwer_module):
    get_html = giro_bouwer_module.get_clickable_image_html

    with patch("os.path.exists", return_value=False):
        html = get_html("test.png", "Fallback", "http://link")
        assert "https://placehold.co/600x400/eeeeee/000000?text=Fallback" in html
        assert "href=\"http://link\"" in html

def test_get_clickable_image_html_exception(giro_bouwer_module):
    get_html = giro_bouwer_module.get_clickable_image_html

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", side_effect=Exception("Read error")):
            html = get_html("test.png", "Fallback", "http://link")
            assert "https://placehold.co/600x400/eeeeee/000000?text=Fallback" in html
            assert "href=\"http://link\"" in html
