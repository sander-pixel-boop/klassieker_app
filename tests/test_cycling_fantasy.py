import pytest
import sys
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Mock Streamlit completely before importing the module
mock_st = MagicMock()
sys.modules['streamlit'] = mock_st
mock_supabase = MagicMock()
sys.modules['supabase'] = mock_supabase
mock_plotly_express = MagicMock()
sys.modules['plotly.express'] = mock_plotly_express
mock_fuzz = MagicMock()
sys.modules['thefuzz'] = mock_fuzz
mock_pypdf = MagicMock()
sys.modules['pypdf'] = mock_pypdf
mock_pulp = MagicMock()
sys.modules['pulp'] = mock_pulp

# Add root directory to sys.path if not there
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="module")
def cf_module():
    # Setup state before importing
    mock_st.session_state = {"ingelogde_speler": "test"}
    mock_st.secrets = {"SUPABASE_URL": "http://mock", "SUPABASE_KEY": "mock"}

    # Mock load_static_data to prevent module-level execution errors
    with patch('pages.Cycling_Fantasy.load_static_data', return_value=pd.DataFrame()):
        import pages.Cycling_Fantasy as cf
        return cf

def test_calculate_cf_ev_ranking(cf_module):
    df = pd.DataFrame({
        'Renner': ['A', 'B', 'C', 'D'],
        'COB': [90, 80, 85, 70],
        'AVG': [80, 85, 80, 70],
        'Prijs': [1000, 500, 800, 200]
    })

    result = cf_module.calculate_cf_ev(df, 'COB', "1. Ranking (CF Punten)")

    assert result.iloc[0]['Renner'] == 'A'
    assert result.iloc[1]['Renner'] == 'C'
    assert result.iloc[2]['Renner'] == 'B'
    assert result.iloc[3]['Renner'] == 'D'

    assert result.iloc[0]['CF_EV'] == 45
    assert result.iloc[1]['CF_EV'] == 25
    assert result.iloc[2]['CF_EV'] == 22
    assert result.iloc[3]['CF_EV'] == 19

    assert result.iloc[0]['Waarde (EV/Credit)'] == round(45 / 1000, 4)
    assert result.iloc[1]['Waarde (EV/Credit)'] == round(25 / 800, 4)

def test_calculate_cf_ev_power_curve(cf_module):
    df = pd.DataFrame({
        'Renner': ['A'],
        'COB': [100],
        'AVG': [80],
        'Prijs': [1000]
    })

    result = cf_module.calculate_cf_ev(df, 'COB', "2. Macht 4 Curve")

    assert result.iloc[0]['CF_EV'] == 45
    assert result.iloc[0]['Waarde (EV/Credit)'] == round(45 / 1000, 4)

    df2 = pd.DataFrame({
        'Renner': ['B'],
        'COB': [50],
        'AVG': [80],
        'Prijs': [1000]
    })
    result2 = cf_module.calculate_cf_ev(df2, 'COB', "2. Macht 4 Curve")
    assert result2.iloc[0]['CF_EV'] == 2.8125

def test_calculate_cf_ev_zero_price_handling(cf_module):
    df = pd.DataFrame({
        'Renner': ['A', 'B'],
        'COB': [90, 80],
        'AVG': [80, 80],
        'Prijs': [0, np.nan]
    })

    result = cf_module.calculate_cf_ev(df, 'COB', "1. Ranking (CF Punten)")

    assert result.iloc[0]['Waarde (EV/Credit)'] == 0.0
    assert result.iloc[1]['Waarde (EV/Credit)'] == 0.0

def test_calculate_cf_ev_ranking_beyond_20(cf_module):
    df = pd.DataFrame({
        'Renner': [f'R{i}' for i in range(25)],
        'COB': [100 - i for i in range(25)],
        'AVG': [50 for i in range(25)],
        'Prijs': [1000 for i in range(25)]
    })

    result = cf_module.calculate_cf_ev(df, 'COB', "1. Ranking (CF Punten)")

    assert len(result) == 25
    assert result.iloc[20]['CF_EV'] == 0.0
    assert result.iloc[24]['CF_EV'] == 0.0
