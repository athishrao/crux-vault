"""CruxVault CLI - Secrets, configs, and feature flags management."""

__version__ = "0.1.0"

from pathlib import Path
from dataclasses import asdict

from cruxvault.storage.local import SQLiteStorage
from cruxvault.crypto.encryption import Encryptor
from cruxvault.utils.utils import get_storage_and_audit

class CruxVault:
    def __init__(self, root: Path = None):
        storage, _ = get_storage_and_audit()
        self._storage = storage

    def get(self, path: str) -> str:
        return self._storage.get_secret(path).value

    def set(self, path: str, value: str, tags: list = None) -> None:
        self._storage.set_secret(path, value, tags=tags)

    def delete(self, path: str) -> bool:
        return self._storage.delete_secret(path)

    def list(self, prefix: str = None, print_: bool = False) -> list:
        secrets = self._storage.list_secrets(prefix)
        
        data = [
            {
                "path": s.path,
                "type": s.type.value,
                "version": s.version,
                "tags": s.tags,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in secrets
        ]
        
        if print_:
            from rich.console import Console
            from rich.table import Table
            
            console = Console()
            table = Table(show_header=True)
            table.add_column("Path")
            table.add_column("Type")
            table.add_column("Version")
            table.add_column("Tags")
            table.add_column("Updated")
            
            for item in data:
                table.add_row(
                    item["path"],
                    item["type"],
                    str(item["version"]),
                    ", ".join(item["tags"]),
                    item["updated_at"][:10]
                )
            
            console.print(table)
            return None
        
        return data

_instance = None
def get(path: str) -> str:
    global _instance
    if not _instance:
        _instance = CruxVault()
    return _instance.get(path)

__all__ = ['CruxVault', 'get', 'set', 'delete', 'list']

