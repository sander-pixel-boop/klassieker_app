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

import datetime

from pages.Het_Spel import is_team_locked

real_datetime = datetime.datetime

@patch('pages.Het_Spel.datetime.datetime')
def test_is_team_locked_before_lock_time(mock_datetime):
    """
    Test that is_team_locked returns False when current time is before the lock time.
    """
    # Mock datetime.now() to return a time before the lock time (e.g., Feb 28, 2025)
    mock_now = real_datetime(2025, 2, 28, 12, 0, tzinfo=datetime.timezone.utc)
    mock_datetime.now.return_value = mock_now
    # We also need to let the mock construct the lock_time correctly,
    # so we side_effect it to fallback to the real datetime when called with arguments
    mock_datetime.side_effect = lambda *args, **kw: real_datetime(*args, **kw)

    result = is_team_locked()
    assert result is False

@patch('pages.Het_Spel.datetime.datetime')
def test_is_team_locked_after_lock_time(mock_datetime):
    """
    Test that is_team_locked returns True when current time is after the lock time.
    """
    # Mock datetime.now() to return a time after the lock time (e.g., March 1, 2025, 12:00)
    mock_now = real_datetime(2025, 3, 1, 12, 0, tzinfo=datetime.timezone.utc)
    mock_datetime.now.return_value = mock_now
    mock_datetime.side_effect = lambda *args, **kw: real_datetime(*args, **kw)

    result = is_team_locked()
    assert result is True

@patch('pages.Het_Spel.datetime.datetime')
def test_is_team_locked_exception(mock_datetime):
    """
    Test that is_team_locked returns False if an exception occurs (e.g., datetime.now fails).
    """
    mock_datetime.now.side_effect = Exception("Mocked exception")
    # For safety, let the lock_time instantiation throw, or let it pass and throw on now()
    # It doesn't matter, an exception should result in False

    result = is_team_locked()
    assert result is False
