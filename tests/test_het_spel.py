import sys
from unittest.mock import MagicMock, patch
import pytest

# Mock modules to prevent side effects on import
mock_st = MagicMock()
# Explicitly mock st.tabs to return three dummy MagicMocks
mock_st.tabs.return_value = (MagicMock(), MagicMock(), MagicMock())

mock_st.secrets = {"CRYPTO_SALT": "test_salt", "SUPABASE_URL": "http://test", "SUPABASE_KEY": "test", "TABEL_NAAM": "test_tabel"}
sys.modules['streamlit'] = mock_st
sys.modules['supabase'] = MagicMock()

# Mock st.cache_data to just return the function itself so it executes normally
def dummy_cache_data(func=None, **kwargs):
    if func is None:
        def wrapper(f):
            return f
        return wrapper
    return func
mock_st.cache_data = dummy_cache_data
# Mock st.cache_resource as well
mock_st.cache_resource = dummy_cache_data

from pages.Sporza.Classics.Het_Spel import is_team_locked, load_game_data, load_csv_data

@patch('pages.Sporza.Classics.Het_Spel.init_connection')
def test_load_game_data_exception_handling(mock_init_connection):
    """
    Test that load_game_data handles exceptions during database operations gracefully
    and returns an empty list.
    """
    # Force init_connection to raise an Exception to simulate connection or query failure
    mock_init_connection.side_effect = Exception("Mocked exception during DB connection")

    # Execute the function
    result = load_game_data()

    # Verify that it caught the exception and returned the fallback empty list
    assert result == []

@patch('pages.Sporza.Classics.Het_Spel.pd.read_csv')
def test_load_csv_data_exception_handling(mock_read_csv):
    """
    Test that load_csv_data handles exceptions during file reading gracefully
    and returns the fallback values.
    """
    # Force pd.read_csv to raise an Exception
    mock_read_csv.side_effect = Exception("Mocked exception during read")

    # Execute the function
    df, races, k_map = load_csv_data()

    # Verify that it caught the exception and returned the fallback values
    assert df['Renner'].tolist() == ['Wout van Aert', 'Mathieu van der Poel', 'Tadej Pogačar']
    assert races == ["NOK", "MSR", "RVV"]
    assert k_map == {}

@patch('pages.Sporza.Classics.Het_Spel.os.path.exists')
@patch('pages.Sporza.Classics.Het_Spel.pd.read_csv')
def test_is_team_locked_exception_handling(mock_read_csv, mock_exists):
    """
    Test that is_team_locked handles exceptions during file reading gracefully
    and returns False.
    """
    # Force os.path.exists to return True so we enter the try block
    mock_exists.return_value = True

    # Force pd.read_csv to raise an Exception
    mock_read_csv.side_effect = Exception("Mocked exception during read")

    # Execute the function
    result = is_team_locked()

    # Verify that it caught the exception and returned False
    assert result is False

@patch('pages.Sporza.Classics.Het_Spel.os.path.exists')
def test_is_team_locked_file_not_found(mock_exists):
    """
    Test that is_team_locked returns False when uitslagen.csv doesn't exist.
    """
    mock_exists.return_value = False

    result = is_team_locked()

    assert result is False

@patch('pages.Sporza.Classics.Het_Spel.os.path.exists')
@patch('pages.Sporza.Classics.Het_Spel.pd.read_csv')
def test_is_team_locked_success(mock_read_csv, mock_exists):
    """
    Test that is_team_locked returns True when NOK is found in the uitslagen.csv
    """
    mock_exists.return_value = True

    # Create a mock dataframe that has 'Race' column and 'NOK' in it
    import pandas as pd
    mock_df = pd.DataFrame({'Race': ['NOK', 'MSR']})
    mock_read_csv.return_value = mock_df

    result = is_team_locked()

    assert result is True

@patch('pages.Sporza.Classics.Het_Spel.os.path.exists')
@patch('pages.Sporza.Classics.Het_Spel.pd.read_csv')
def test_is_team_locked_no_nok(mock_read_csv, mock_exists):
    """
    Test that is_team_locked returns False when NOK is NOT found in the uitslagen.csv
    """
    mock_exists.return_value = True

    import pandas as pd
    mock_df = pd.DataFrame({'Race': ['MSR', 'E3']})
    mock_read_csv.return_value = mock_df

    result = is_team_locked()

    assert result is False

@patch('pages.Sporza.Classics.Het_Spel.os.path.exists')
@patch('pages.Sporza.Classics.Het_Spel.pd.read_csv')
def test_is_team_locked_no_race_column(mock_read_csv, mock_exists):
    """
    Test that is_team_locked returns False when uitslagen.csv doesn't have a Race column
    """
    mock_exists.return_value = True

    import pandas as pd
    mock_df = pd.DataFrame({'Other': ['A', 'B']})
    mock_read_csv.return_value = mock_df

    result = is_team_locked()

    assert result is False
