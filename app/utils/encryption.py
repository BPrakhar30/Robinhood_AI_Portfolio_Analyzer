"""Fernet symmetric encryption for broker OAuth tokens at rest.

Fintech expectation: tokens must never be stored plaintext. ``get_encryptor()``
returns a process-wide singleton so all callers share one key-backed Fernet
instance. If ``encryption_key`` is unset, a random key is generated in memory
— ciphertext becomes unreadable after restart until a stable key is configured.

Added: 2026-04-03
"""
from cryptography.fernet import Fernet, InvalidToken
from app.config import get_settings
from app.utils.exceptions import EncryptionError


class TokenEncryptor:
    """
    Encrypts and decrypts broker tokens using Fernet symmetric encryption.
    Tokens are never stored in plaintext — this is a fintech-level requirement.
    """

    def __init__(self):
        settings = get_settings()
        key = settings.encryption_key
        if not key:
            # Ephemeral key: fine for local experiments; production must set ENCRYPTION_KEY.
            key = Fernet.generate_key().decode()
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise EncryptionError(f"Invalid encryption key: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypts a plaintext string (e.g. OAuth token).

        Parameters:
            plaintext: The token to encrypt

        Returns:
            Encrypted token as a base64-encoded string

        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            return ""
        try:
            return self._fernet.encrypt(plaintext.encode()).decode()
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypts an encrypted token back to plaintext.

        Parameters:
            encrypted_text: The encrypted token string

        Returns:
            Decrypted plaintext token

        Raises:
            EncryptionError: If decryption fails (wrong key, corrupted data)
        """
        if not encrypted_text:
            return ""
        try:
            return self._fernet.decrypt(encrypted_text.encode()).decode()
        except InvalidToken:
            raise EncryptionError("Decryption failed: invalid token or wrong key")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")


_encryptor: TokenEncryptor | None = None


def get_encryptor() -> TokenEncryptor:
    # Lazy singleton — first caller initializes; avoids import-time side effects.
    global _encryptor
    if _encryptor is None:
        _encryptor = TokenEncryptor()
    return _encryptor
