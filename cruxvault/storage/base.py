from abc import ABC, abstractmethod
from typing import Optional

from cruxvault.models import Secret, SecretVersion


class StorageBackend(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initialize storage backend (create tables, files, etc.)."""
        pass

    @abstractmethod
    def set_secret(
        self, path: str, value: str, secret_type: str = "secret", tags: Optional[list[str]] = None
    ) -> Secret:
        """Store or update a secret.

        Args:
            path: Secret path
            value: Secret value (will be encrypted)
            secret_type: Type of secret
            tags: Optional tags

        Returns:
            Created/updated Secret
        """
        pass

    @abstractmethod
    def get_secret(self, path: str) -> Optional[Secret]:
        """Retrieve a secret by path.

        Args:
            path: Secret path

        Returns:
            Secret if found, None otherwise
        """
        pass

    @abstractmethod
    def list_secrets(self, prefix: Optional[str] = None) -> list[Secret]:
        """List all secrets, optionally filtered by prefix.

        Args:
            prefix: Optional path prefix filter

        Returns:
            List of secrets
        """
        pass

    @abstractmethod
    def delete_secret(self, path: str) -> bool:
        """Delete a secret.

        Args:
            path: Secret path

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def get_history(self, path: str) -> list[SecretVersion]:
        """Get version history for a secret.

        Args:
            path: Secret path

        Returns:
            List of secret versions, newest first
        """
        pass

    @abstractmethod
    def rollback(self, path: str, version: int) -> Secret:
        """Rollback a secret to a specific version.

        Args:
            path: Secret path
            version: Version number to rollback to

        Returns:
            Updated Secret

        Raises:
            ValueError: If version not found
        """
        pass


    @abstractmethod
    def close(self) -> None:
        """Close storage backend connections."""
        pass

