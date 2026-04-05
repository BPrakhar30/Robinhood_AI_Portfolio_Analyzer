import os
import pytest
from cryptography.fernet import Fernet

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from app.utils.encryption import TokenEncryptor


def test_encrypt_decrypt_roundtrip():
    encryptor = TokenEncryptor()
    original = "my-secret-access-token-12345"
    encrypted = encryptor.encrypt(original)
    assert encrypted != original
    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == original


def test_encrypt_empty_string():
    encryptor = TokenEncryptor()
    assert encryptor.encrypt("") == ""
    assert encryptor.decrypt("") == ""


def test_encrypt_produces_different_output():
    encryptor = TokenEncryptor()
    token = "same-token"
    enc1 = encryptor.encrypt(token)
    enc2 = encryptor.encrypt(token)
    # Fernet uses random IV so same plaintext produces different ciphertext
    assert enc1 != enc2
    assert encryptor.decrypt(enc1) == token
    assert encryptor.decrypt(enc2) == token


def test_decrypt_wrong_key():
    encryptor1 = TokenEncryptor()
    encrypted = encryptor1.encrypt("secret")

    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    encryptor2 = TokenEncryptor()

    from app.utils.exceptions import EncryptionError
    with pytest.raises(EncryptionError):
        encryptor2.decrypt(encrypted)
