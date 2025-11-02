import os
import tempfile
from datetime import datetime

import pytest

from cruxvault.crypto.encryption import Encryptor
from cruxvault.models import AuditEntry, SecretType
from cruxvault.storage.local import SQLiteStorage


@pytest.fixture
def temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def storage(temp_db: str) -> SQLiteStorage:
    encryptor = Encryptor()
    storage = SQLiteStorage(temp_db, encryptor)
    storage.initialize()
    return storage


class TestSQLiteStorage:

    def test_initialize(self, temp_db: str) -> None:
        encryptor = Encryptor()
        storage = SQLiteStorage(temp_db, encryptor)
        storage.initialize()

        assert os.path.exists(temp_db)

    def test_set_and_get_secret(self, storage: SQLiteStorage) -> None:
        path = "database/password"
        value = "super-secret-123"

        secret = storage.set_secret(path, value)

        assert secret.path == path
        assert secret.value == value
        assert secret.version == 1
        assert secret.type == SecretType.SECRET

        retrieved = storage.get_secret(path)

        assert retrieved is not None
        assert retrieved.path == path
        assert retrieved.value == value
        assert retrieved.version == 1

    def test_get_nonexistent_secret(self, storage: SQLiteStorage) -> None:
        result = storage.get_secret("nonexistent/path")
        assert result is None

    def test_update_secret_increments_version(self, storage: SQLiteStorage) -> None:
        path = "api/key"

        secret1 = storage.set_secret(path, "value1")
        assert secret1.version == 1

        secret2 = storage.set_secret(path, "value2")
        assert secret2.version == 2

        retrieved = storage.get_secret(path)
        assert retrieved is not None
        assert retrieved.value == "value2"
        assert retrieved.version == 2

    def test_set_secret_with_tags(self, storage: SQLiteStorage) -> None:
        path = "stripe/key"
        tags = ["production", "payment"]

        secret = storage.set_secret(path, "value", tags=tags)
        assert secret.tags == tags

        retrieved = storage.get_secret(path)
        assert retrieved is not None
        assert retrieved.tags == tags

    def test_set_secret_with_type(self, storage: SQLiteStorage) -> None:
        storage.set_secret("db/host", "localhost", secret_type="config")
        storage.set_secret("feature/new_ui", "true", secret_type="flag")

        config = storage.get_secret("db/host")
        flag = storage.get_secret("feature/new_ui")

        assert config is not None
        assert config.type == SecretType.CONFIG

        assert flag is not None
        assert flag.type == SecretType.FLAG

    def test_list_secrets(self, storage: SQLiteStorage) -> None:
        storage.set_secret("api/key1", "value1")
        storage.set_secret("api/key2", "value2")
        storage.set_secret("database/password", "value3")

        secrets = storage.list_secrets()

        assert len(secrets) == 3
        paths = [s.path for s in secrets]
        assert "api/key1" in paths
        assert "api/key2" in paths
        assert "database/password" in paths

    def test_list_secrets_with_prefix(self, storage: SQLiteStorage) -> None:
        storage.set_secret("api/key1", "value1")
        storage.set_secret("api/key2", "value2")
        storage.set_secret("database/password", "value3")

        api_secrets = storage.list_secrets(prefix="api/")

        assert len(api_secrets) == 2
        paths = [s.path for s in api_secrets]
        assert "api/key1" in paths
        assert "api/key2" in paths
        assert "database/password" not in paths

    def test_delete_secret(self, storage: SQLiteStorage) -> None:
        path = "temp/secret"
        storage.set_secret(path, "value")

        result = storage.delete_secret(path)
        assert result is True

        retrieved = storage.get_secret(path)
        assert retrieved is None

    def test_delete_nonexistent_secret(self, storage: SQLiteStorage) -> None:
        result = storage.delete_secret("nonexistent")
        assert result is False

    def test_get_history(self, storage: SQLiteStorage) -> None:
        path = "api/key"

        storage.set_secret(path, "value1")
        storage.set_secret(path, "value2")
        storage.set_secret(path, "value3")

        history = storage.get_history(path)

        assert len(history) == 3

        assert history[0].version == 3
        assert history[0].value == "value3"
        assert history[1].version == 2
        assert history[1].value == "value2"
        assert history[2].version == 1
        assert history[2].value == "value1"

    def test_get_history_nonexistent(self, storage: SQLiteStorage) -> None:
        history = storage.get_history("nonexistent")
        assert len(history) == 0

    def test_rollback(self, storage: SQLiteStorage) -> None:
        path = "api/key"

        storage.set_secret(path, "value1")
        storage.set_secret(path, "value2")
        storage.set_secret(path, "value3")

        rolled_back = storage.rollback(path, 1)

        assert rolled_back.value == "value1"
        assert rolled_back.version == 4  # New version number

        current = storage.get_secret(path)
        assert current is not None
        assert current.value == "value1"

    def test_rollback_nonexistent_version(self, storage: SQLiteStorage) -> None:
        path = "api/key"
        storage.set_secret(path, "value")

        with pytest.raises(ValueError, match="Version .* not found"):
            storage.rollback(path, 999)

    def test_rollback_nonexistent_secret(self, storage: SQLiteStorage) -> None:
        with pytest.raises(ValueError, match="not found"):
            storage.rollback("nonexistent", 1)

    def test_log_audit(self, storage: SQLiteStorage) -> None:
        entry = AuditEntry(
            user="testuser",
            action="set",
            path="test/path",
            success=True,
        )

        storage.log_audit(entry)


    def test_values_are_encrypted_at_rest(self, storage: SQLiteStorage) -> None:
        path = "secret/path"
        value = "plaintext-value"

        storage.set_secret(path, value)

        from sqlalchemy import select, text

        with storage.SessionLocal() as session:
            result = session.execute(text("SELECT encrypted_value FROM secrets WHERE path = :path"), {"path": path})
            row = result.fetchone()

            assert row is not None
            encrypted_value = row[0]

            assert encrypted_value != value

            assert len(encrypted_value) > len(value)

    def test_close(self, storage: SQLiteStorage) -> None:
        storage.close()

