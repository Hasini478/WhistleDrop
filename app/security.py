"""Cryptographic security utilities for WhistleDrop.

Handles unguessable case code generation and HMAC-SHA256 one-way hashing
to protect reporter case codes even against database compromises.
"""

import hmac
import hashlib
import secrets
from typing import Optional


def generate_case_code() -> str:
    """Generate a cryptographically secure, unpredictable case code.

    Format: WD-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    Provides 128 bits of cryptographic entropy using Python's secrets module.
    """
    token = secrets.token_hex(16).upper()
    parts = [token[i : i + 4] for i in range(0, 32, 4)]
    return f"WD-{'-'.join(parts)}"


def hash_case_code(case_code: str, secret_key: str) -> str:
    """Compute a deterministic HMAC-SHA256 digest of the normalized case code.

    The case code is normalized (stripped and uppercase) so valid codes
    can be looked up reliably in constant time without storing the plaintext code.
    """
    normalized_code = case_code.strip().upper()
    return hmac.new(
        secret_key.encode("utf-8"),
        normalized_code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def safe_compare(val_a: Optional[str], val_b: Optional[str]) -> bool:
    """Compare two strings in constant time to avoid timing attacks."""
    if val_a is None or val_b is None:
        return False
    return secrets.compare_digest(val_a, val_b)
