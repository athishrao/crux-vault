import pytest

from cruxvault.crypto.encryption import AESGCM, Encryptor, EncryptionError


class TestEncryptor:
    def test_encrypt_decrypt(self) -> None:
        encryptor = Encryptor()
        plaintext = "my-super-secret-password"

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext
        assert len(encrypted) > len(plaintext)

    def test_encrypt_with_custom_key(self) -> None:
        key = Encryptor.generate_key()
        encryptor = Encryptor(key)

        plaintext = "test-secret"
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_decrypt_with_different_key_fails(self) -> None:
        encryptor1 = Encryptor()
        encryptor2 = Encryptor()

        plaintext = "secret"
        encrypted = encryptor1.encrypt(plaintext)

        with pytest.raises(EncryptionError):
            encryptor2.decrypt(encrypted)

    def test_encrypt_empty_string(self) -> None:
        encryptor = Encryptor()
        plaintext = ""

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_unicode(self) -> None:
        encryptor = Encryptor()
        plaintext = "🔒 secret with émojis and àccents 中文"

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_long_string(self) -> None:
        encryptor = Encryptor()
        plaintext = "x" * 10000

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_invalid_master_key_length(self) -> None:
        with pytest.raises(EncryptionError):
            Encryptor(b"too-short")

    def test_decrypt_invalid_data(self) -> None:
        encryptor = Encryptor()

        with pytest.raises(EncryptionError):
            encryptor.decrypt("invalid-base64-data")

    def test_key_generation(self) -> None:
        key1 = Encryptor.generate_key()
        key2 = Encryptor.generate_key()

        assert len(key1) == 32
        assert len(key2) == 32
        assert key1 != key2

    def test_key_to_string_and_back(self) -> None:
        key = Encryptor.generate_key()
        key_string = Encryptor.key_to_string(key)
        key_back = Encryptor.string_to_key(key_string)

        assert key == key_back
        assert isinstance(key_string, str)

    def test_same_plaintext_different_ciphertext(self) -> None:
        encryptor = Encryptor()
        plaintext = "secret"

        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)

        assert encrypted1 != encrypted2
        assert encryptor.decrypt(encrypted1) == plaintext
        assert encryptor.decrypt(encrypted2) == plaintext

