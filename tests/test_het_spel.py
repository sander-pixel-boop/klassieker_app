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

from pages.Het_Spel import is_team_locked
from datetime import datetime, timezone

@patch('pages.Het_Spel.datetime')
def test_is_team_locked_before_lock_time(mock_datetime):
    """
    Test that is_team_locked returns False before the lock time.
    """
    # Create a proper datetime mock that acts like the real class but returns our fixed 'now'
    mock_datetime.now.return_value = datetime(2025, 2, 28, 11, 0, tzinfo=timezone.utc)

    # Ensure that datetime(...) in the source code returns the correct value for lock_time
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    result = is_team_locked()

    assert result is False

@patch('pages.Het_Spel.datetime')
def test_is_team_locked_after_lock_time(mock_datetime):
    """
    Test that is_team_locked returns True after the lock time.
    """
    mock_datetime.now.return_value = datetime(2025, 3, 1, 11, 1, tzinfo=timezone.utc)
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    result = is_team_locked()

    assert result is True

@patch('pages.Het_Spel.datetime')
def test_is_team_locked_exception(mock_datetime):
    """
    Test that is_team_locked returns False if an exception is raised.
    """
    mock_datetime.now.side_effect = Exception("Some time error")
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    result = is_team_locked()

    assert result is False
