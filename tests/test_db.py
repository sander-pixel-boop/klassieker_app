import sys
import pytest
from unittest.mock import MagicMock

# Create mocks
mock_st = MagicMock()
mock_st.secrets = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-key-123"
}

# Mock the decorator to just return the function
def mock_cache_resource(func):
    return func
mock_st.cache_resource = mock_cache_resource

mock_supabase = MagicMock()
mock_client_instance = MagicMock()
mock_supabase.create_client.return_value = mock_client_instance

# Inject mocks
sys.modules["streamlit"] = mock_st
sys.modules["supabase"] = mock_supabase

# Now import the module to test
from utils.db import init_connection

def test_init_connection_success():
    """Test that init_connection correctly initializes the Supabase client with secrets."""
    # Reset mock to ensure clean state
    mock_supabase.create_client.reset_mock()

    # Call the function
    client = init_connection()

    # Verify create_client was called with correct arguments from secrets
    mock_supabase.create_client.assert_called_once_with(
        "https://test.supabase.co",
        "test-key-123"
    )

    # Verify the returned client is the one from create_client
    assert client == mock_client_instance

def test_init_connection_missing_secrets():
    """Test that init_connection raises a KeyError when secrets are missing."""
    # Temporarily remove a secret
    original_url = mock_st.secrets.pop("SUPABASE_URL")

    with pytest.raises(KeyError):
        init_connection()

    # Restore the secret
    mock_st.secrets["SUPABASE_URL"] = original_url
