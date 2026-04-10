import json
import hashlib
import os
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
    Hashes a password using PBKDF2-HMAC-SHA256 with a random salt.
    Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    iterations = 600000
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac('sha256', wachtwoord.encode('utf-8'), salt.encode('utf-8'), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"

def verify_wachtwoord(wachtwoord, db_hash):
    """
    Verifies a password against a stored database hash.
    Supports both new PBKDF2 formats and legacy unsalted SHA-256 formats.
    """
    if db_hash.startswith("pbkdf2_sha256$"):
        parts = db_hash.split("$")
        if len(parts) == 4:
            _, iterations_str, salt, stored_hash = parts
            iterations = int(iterations_str)
            dk = hashlib.pbkdf2_hmac('sha256', wachtwoord.encode('utf-8'), salt.encode('utf-8'), iterations)
            return dk.hex() == stored_hash
        return False
    else:
        # Legacy unsalted SHA-256 validation
        return hashlib.sha256(wachtwoord.encode('utf-8')).hexdigest() == db_hash
