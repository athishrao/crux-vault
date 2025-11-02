import os
import keyring

from cruxvault.crypto.encryption import Encryptor

KEYRING_SERVICE = "cruxvault-cli"
KEYRING_USERNAME = "master-key"

def get_or_create_master_key() -> bytes:
    try:
        key_string = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if key_string:
            return Encryptor.string_to_key(key_string)
    except Exception:
        pass

    env_key = os.getenv("UNIFIED_MASTER_KEY")
    if env_key:
        try:
            return Encryptor.string_to_key(env_key)
        except Exception:
            pass

    key = Encryptor.generate_key()

    # Try to save to keyring
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, Encryptor.key_to_string(key))
    except Exception:
        print_warning(
            "Could not save master key to system keychain. "
            f"Set UNIFIED_MASTER_KEY environment variable to: {Encryptor.key_to_string(key)}"
        )

    return key
