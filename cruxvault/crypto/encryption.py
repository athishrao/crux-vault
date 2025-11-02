import base64
import os
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionError(Exception):
    pass


class Encryptor:
    def __init__(self, master_key: Optional[bytes] = None) -> None:
        if master_key is None:
            master_key = AESGCM.generate_key(bit_length=256)
        elif len(master_key) != 32:
            raise EncryptionError("Master key must be exactly 32 bytes for AES-256")

        self.master_key = master_key
        self.aesgcm = AESGCM(master_key)

    def encrypt(self, plaintext: str) -> str:
        try:
            nonce = os.urandom(12)

            plaintext_bytes = plaintext.encode("utf-8")
            ciphertext = self.aesgcm.encrypt(nonce, plaintext_bytes, None)

            combined = nonce + ciphertext
            return base64.b64encode(combined).decode("utf-8")

        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, encrypted: str) -> str:
        try:
            combined = base64.b64decode(encrypted.encode("utf-8"))

            # Split nonce and ciphertext
            nonce = combined[:12]
            ciphertext = combined[12:]

            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode("utf-8")

        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}") from e

    @staticmethod
    def generate_key() -> bytes:
        return AESGCM.generate_key(bit_length=256)

    @staticmethod
    def key_to_string(key: bytes) -> str:
        return base64.b64encode(key).decode("utf-8")

    @staticmethod
    def string_to_key(key_string: str) -> bytes:
        return base64.b64decode(key_string.encode("utf-8"))

