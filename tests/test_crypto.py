import pytest
from unittest.mock import MagicMock
import sys

# Mock streamlit before importing utils.crypto
mock_st = MagicMock()
mock_st.secrets = {"CRYPTO_SALT": "GeheimeKlassiekerSleutel2026"}
sys.modules["streamlit"] = mock_st

from utils.crypto import generate_signature

def test_generate_signature_basic():
    data = {"name": "Wout", "team": "Visma"}
    sig = generate_signature(data)
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex length

def test_generate_signature_deterministic():
    data1 = {"a": 1, "b": 2}
    data2 = {"b": 2, "a": 1}
    # generate_signature should sort keys, so these should match
    assert generate_signature(data1) == generate_signature(data2)

def test_generate_signature_distinct():
    data1 = {"a": 1}
    data2 = {"a": 2}
    assert generate_signature(data1) != generate_signature(data2)

def test_generate_signature_nested():
    data1 = {"user": "test", "picks": {"race1": "Rider A"}}
    data2 = {"picks": {"race1": "Rider A"}, "user": "test"}
    assert generate_signature(data1) == generate_signature(data2)

def test_generate_signature_empty():
    assert isinstance(generate_signature({}), str)

def test_generate_signature_with_salt_verification():
    # If the salt or implementation changes, this test will fail.
    # This ensures we don't accidentally break compatibility with existing signatures.
    data = {"test": True}
    # Based on: json.dumps({"test": True}, sort_keys=True) + "GeheimeKlassiekerSleutel2026"
    expected_sig = "a1362e9a9fc4c46280bf83d5b952e452ae805d3653e93d95a825ea5e6a515e0a"
    assert generate_signature(data) == expected_sig

def test_generate_signature_with_different_salt():
    # Verify that changing the salt changes the signature
    mock_st.secrets["CRYPTO_SALT"] = "DifferentSalt"
    data = {"test": True}
    sig1 = "a1362e9a9fc4c46280bf83d5b952e452ae805d3653e93d95a825ea5e6a515e0a"
    assert generate_signature(data) != sig1

    # Reset salt for other tests if necessary (though they might run in parallel or different order)
    mock_st.secrets["CRYPTO_SALT"] = "GeheimeKlassiekerSleutel2026"
