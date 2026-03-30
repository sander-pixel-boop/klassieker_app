import json
import hashlib

def generate_signature(data_dict):
    """
    Generates a SHA-256 hash for a given dictionary.
    Keys are sorted to ensure deterministic output.
    """
    data_str = json.dumps(data_dict, sort_keys=True)
    salt = "GeheimeKlassiekerSleutel2026"
    return hashlib.sha256((data_str + salt).encode('utf-8')).hexdigest()
