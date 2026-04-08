import json
import hashlib
import hmac
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

def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a random salt.
    Format: pbkdf2_sha256$<iterations>$<salt>$<hash>
    """
    salt = os.urandom(16)
    iterations = 600000
    hash_bytes = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations
    )

    salt_hex = salt.hex()
    hash_hex = hash_bytes.hex()

    return f"pbkdf2_sha256${iterations}${salt_hex}${hash_hex}"

def verify_password(password: str, hashed: str) -> bool:
    """
    Verifies a password against a hash.
    Supports both new PBKDF2 hashes and legacy SHA256 hashes.
    """
    if hashed.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed.split("$")
            if len(parts) != 4:
                return False

            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            original_hash = bytes.fromhex(parts[3])

            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations
            )

            return hmac.compare_digest(new_hash, original_hash)
        except (ValueError, TypeError):
            return False
    else:
        # Legacy SHA256 hash (unsalted)
        legacy_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return hmac.compare_digest(legacy_hash, hashed)
