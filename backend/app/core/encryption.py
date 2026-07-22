"""Secrets encryption at rest using Fernet symmetric encryption.

Encrypts sensitive values (API keys) before storing them in the database.
Uses a machine-derived key by default, or a user-provided passphrase.
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from app.core.logging import get_logger

logger = get_logger("encryption")


def _derive_key(passphrase: str | None = None) -> bytes:
    """Derive a Fernet key from a passphrase or machine ID.

    If no passphrase is provided, uses a combination of:
    - TERRAMORPH_ENCRYPTION_KEY env var (if set)
    - Machine-specific fallback (hostname + data path)
    """
    if passphrase:
        # Derive from user passphrase
        key_material = passphrase.encode()
    else:
        # Use env var or stable fallback
        env_key = os.environ.get("TERRAMORPH_ENCRYPTION_KEY", "")
        if env_key:
            key_material = env_key.encode()
        else:
            # Stable fallback: use the data directory path (doesn't change between restarts)
            data_dir = os.environ.get("TERRAMORPH_DATA_DIR", "/app/data")
            key_material = f"terramorph-secrets:{data_dir}:stable-key-v1".encode()

    # Derive 32 bytes using SHA-256 and encode as Fernet key
    derived = hashlib.sha256(key_material).digest()
    return base64.urlsafe_b64encode(derived)


def _get_fernet() -> Fernet:
    """Get a Fernet instance with the current key."""
    key = _derive_key()
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a string value.

    Args:
        plaintext: The secret to encrypt.

    Returns:
        Encrypted string (base64 encoded).
    """
    if not plaintext:
        return ""
    try:
        f = _get_fernet()
        encrypted = f.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return plaintext  # Fallback to plaintext if encryption fails


def decrypt(ciphertext: str) -> str:
    """Decrypt an encrypted string value.

    Args:
        ciphertext: The encrypted value.

    Returns:
        Decrypted plaintext string.
    """
    if not ciphertext:
        return ""
    try:
        f = _get_fernet()
        decrypted = f.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken:
        # If decryption fails, the value might be stored in plaintext (legacy)
        logger.warning("Decryption failed — value may be stored in plaintext (legacy)")
        return ciphertext
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ciphertext
