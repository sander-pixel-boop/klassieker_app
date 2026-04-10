import pytest
from unittest.mock import MagicMock
import sys
import hashlib

# Mock streamlit before importing utils.crypto
mock_st = MagicMock()
mock_st.secrets = {"CRYPTO_SALT": "GeheimeKlassiekerSleutel2026"}
sys.modules["streamlit"] = mock_st

from utils.crypto import generate_signature, hash_wachtwoord, verify_wachtwoord

def test_hash_wachtwoord_format():
    ww = "test1234"
    hashed = hash_wachtwoord(ww)
    assert hashed.startswith("pbkdf2_sha256$600000$")
    parts = hashed.split("$")
    assert len(parts) == 4
    # The salt should be 32 hex chars (16 bytes)
    assert len(parts[2]) == 32
    # The hash should be 64 hex chars (32 bytes)
    assert len(parts[3]) == 64

def test_hash_wachtwoord_is_salted():
    ww = "test1234"
    # Even with same password, salting should result in different hashes
    assert hash_wachtwoord(ww) != hash_wachtwoord(ww)

def test_verify_wachtwoord_pbkdf2():
    ww = "cycling2024"
    hashed = hash_wachtwoord(ww)
    assert verify_wachtwoord(ww, hashed) is True
    assert verify_wachtwoord("wrongpassword", hashed) is False

def test_verify_wachtwoord_legacy():
    ww = "legacy123"
    legacy_hash = hashlib.sha256(ww.encode()).hexdigest()
    assert verify_wachtwoord(ww, legacy_hash) is True
    assert verify_wachtwoord("wrongpassword", legacy_hash) is False

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
