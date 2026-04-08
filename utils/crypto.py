import json
import hashlib
import streamlit as st

def generate_signature(data_dict):
    """
    Generates a SHA-256 hash for a given dictionary.
    Keys are sorted to ensure deterministic output.
    """
    data_str = json.dumps(data_dict, sort_keys=True)
    salt = st.secrets["CRYPTO_SALT"]
    return hashlib.sha256((data_str + salt).encode('utf-8')).hexdigest()

def hash_wachtwoord(wachtwoord):
    """
    Hashes a password using SHA-256.
    """
    return hashlib.sha256(wachtwoord.encode()).hexdigest()
